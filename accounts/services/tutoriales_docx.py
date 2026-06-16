import re
import unicodedata
import zipfile
from dataclasses import dataclass
from io import BytesIO
from xml.etree import ElementTree

from django.db import transaction

from accounts.models import Procedimiento


W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W_NS}


@dataclass
class TutorialDocxItem:
    orden: int
    titulo: str
    categoria: str
    descripcion: str
    contenido: str
    documento: str
    activo: bool


def _w_attr(name):
    return f"{{{W_NS}}}{name}"


def _read_docx_xml(uploaded_file):
    uploaded_file.seek(0)
    data = uploaded_file.read()
    try:
        with zipfile.ZipFile(BytesIO(data)) as docx:
            document_xml = docx.read("word/document.xml")
    except (KeyError, zipfile.BadZipFile) as exc:
        raise ValueError("El archivo no parece ser un DOCX valido.") from exc
    return ElementTree.fromstring(document_xml)


def _paragraph_text(paragraph):
    parts = []
    for node in paragraph.iter():
        if node.tag == f"{{{W_NS}}}t":
            parts.append(node.text or "")
        elif node.tag == f"{{{W_NS}}}tab":
            parts.append("\t")
    return "".join(parts).strip()


def _paragraph_style(paragraph):
    p_style = paragraph.find("./w:pPr/w:pStyle", NS)
    if p_style is None:
        return ""
    return p_style.attrib.get(_w_attr("val"), "")


def _extract_paragraphs(root):
    paragraphs = []
    body = root.find("w:body", NS)
    if body is None:
        return paragraphs
    for paragraph in body.findall(".//w:p", NS):
        text = _paragraph_text(paragraph)
        if text:
            paragraphs.append({"style": _paragraph_style(paragraph), "text": text})
    return paragraphs


def _cell_text(cell):
    values = []
    for paragraph in cell.findall(".//w:p", NS):
        text = _paragraph_text(paragraph)
        if text:
            values.append(text)
    return " ".join(values).strip()


def _extract_appendix_documents(root):
    documents = {}
    body = root.find("w:body", NS)
    if body is None:
        return documents
    for table in body.findall(".//w:tbl", NS):
        rows = []
        for row in table.findall("./w:tr", NS):
            cells = [_cell_text(cell) for cell in row.findall("./w:tc", NS)]
            if cells:
                rows.append(cells)
        for cells in rows[1:]:
            if len(cells) >= 4 and cells[1] and cells[3]:
                documents[cells[1].strip()] = cells[3].strip()
    return documents


def _style_key(style):
    normalized = unicodedata.normalize("NFKD", style or "")
    ascii_text = "".join(char for char in normalized if not unicodedata.combining(char))
    return ascii_text.lower().replace(" ", "")


def _is_heading_one(paragraph):
    return _style_key(paragraph["style"]) in {"heading1", "titulo1", "ttulo1"}


def _is_heading_two(paragraph):
    return _style_key(paragraph["style"]) in {"heading2", "titulo2", "ttulo2"}


def _parse_heading(text):
    match = re.match(r"^\s*(\d+)\.\s+(.+?)\s*$", text)
    if not match:
        return None
    return int(match.group(1)), match.group(2).strip()


def _parse_meta(text, heading_order):
    meta = {
        "categoria": "",
        "orden": heading_order * 10,
        "activo": True,
    }
    chunks = [part.strip() for part in text.split("|") if part.strip()]
    for chunk in chunks:
        if ":" not in chunk:
            continue
        label, value = [part.strip() for part in chunk.split(":", 1)]
        label = label.lower()
        if label == "categoria":
            meta["categoria"] = value
        elif label == "orden visual":
            try:
                meta["orden"] = int(value)
            except ValueError:
                meta["orden"] = heading_order * 10
        elif label == "estado":
            meta["activo"] = value.lower() not in {"oculto", "inactivo", "no publicado"}
    return meta


def _strip_manual_number(text):
    return re.sub(r"^\s*\d+\.\s+", "", text).strip()


def parse_tutoriales_docx(uploaded_file):
    root = _read_docx_xml(uploaded_file)
    paragraphs = _extract_paragraphs(root)
    appendix_documents = _extract_appendix_documents(root)

    tutorials = []
    index = 0
    while index < len(paragraphs):
        paragraph = paragraphs[index]
        heading = _parse_heading(paragraph["text"]) if _is_heading_one(paragraph) else None
        if not heading:
            index += 1
            continue

        heading_order, title = heading
        block = []
        index += 1
        while index < len(paragraphs):
            next_paragraph = paragraphs[index]
            next_heading = _parse_heading(next_paragraph["text"]) if _is_heading_one(next_paragraph) else None
            if next_heading or next_paragraph["text"].lower().startswith("anexo:"):
                break
            block.append(next_paragraph)
            index += 1

        meta = _parse_meta(block[0]["text"], heading_order) if block else _parse_meta("", heading_order)
        section = ""
        descripcion_lines = []
        paso_lines = []
        documento_lines = []

        for item in block[1:] if block else []:
            text = item["text"].strip()
            lower = text.lower()
            if _is_heading_two(item):
                if lower == "cuando usarlo":
                    section = "descripcion"
                elif lower == "pasos a seguir":
                    section = "pasos"
                elif lower == "documento completo de apoyo":
                    section = "documento"
                else:
                    section = ""
                continue

            if section == "descripcion":
                descripcion_lines.append(text)
            elif section == "pasos":
                paso_lines.append(_strip_manual_number(text))
            elif section == "documento":
                documento_lines.append(text)

        documento = "\n".join(documento_lines).strip() or appendix_documents.get(title, "")
        tutorials.append(
            TutorialDocxItem(
                orden=meta["orden"],
                titulo=title,
                categoria=meta["categoria"],
                descripcion=" ".join(descripcion_lines).strip(),
                contenido="\n".join(f"{idx}. {paso}" for idx, paso in enumerate(paso_lines, 1)),
                documento=documento,
                activo=meta["activo"],
            )
        )

    if not tutorials:
        raise ValueError(
            "No se encontraron tutoriales. Usa el documento base con titulos numerados y secciones 'Cuando usarlo', 'Pasos a seguir' y 'Documento completo de apoyo'."
        )
    return tutorials


@transaction.atomic
def importar_tutoriales_docx(uploaded_file, user):
    tutoriales = parse_tutoriales_docx(uploaded_file)
    creados = 0
    actualizados = 0

    for tutorial in tutoriales:
        procedimiento, created = Procedimiento.objects.get_or_create(
            titulo=tutorial.titulo,
            defaults={
                "creado_por": user,
                "responsable": user,
            },
        )
        if created:
            creados += 1
        else:
            actualizados += 1

        procedimiento.tipo = Procedimiento.TIPO_PROCEDIMIENTO
        procedimiento.categoria = tutorial.categoria
        procedimiento.descripcion = tutorial.descripcion
        procedimiento.contenido = tutorial.contenido
        if tutorial.documento:
            procedimiento.enlace = tutorial.documento
        procedimiento.orden = tutorial.orden
        procedimiento.activo = tutorial.activo
        procedimiento.estado = Procedimiento.ESTADO_PENDIENTE
        procedimiento.prioridad = Procedimiento.PRIORIDAD_ALTA
        procedimiento.fecha_compromiso = None
        procedimiento.resultado = ""
        procedimiento.responsable = procedimiento.responsable or user
        procedimiento.actualizado_por = user
        procedimiento.save()

    return {
        "total": len(tutoriales),
        "creados": creados,
        "actualizados": actualizados,
    }
