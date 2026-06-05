"""Propuesta COMPLETA (no solo la económica): secciones boilerplate + narrativas.

Genera una propuesta técnico-económica al estilo CiiSA usando un precedente como
plantilla. Estrategia "punto medio" por sección:
  - Acerca de CiiSA / Confidencialidad → texto FIJO (boilerplate, solo se inyecta el
    nombre del cliente).
  - Objetivo / Alcances / Limitantes / Términos / Condiciones comerciales → las redacta
    el LLM adaptando el precedente al pedido.
  - Económica (ítems/precios) → la maneja ``extractor.draft_from_precedent`` (QuoteDraft).
"""
from __future__ import annotations

import asyncio

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from app.quotes.extractor import _parse_json, draft_from_precedent
from app.quotes.schema import QuoteDraft
from app.services.llm import get_chat_llm


# ── Modelo ──────────────────────────────────────────────────────────────────────


class ProposalSection(BaseModel):
    """Una sección de texto de la propuesta (editable en el front)."""

    key: str
    titulo: str
    contenido: str = ""
    fuente: str = "generado"  # "fijo" | "precedente" | "generado"


class ProposalDraft(BaseModel):
    """Propuesta completa: secciones de texto + la cotización económica embebida."""

    kind: str = "proposal"  # discrimina de un QuoteDraft suelto en Quote.data
    cliente: str | None = None
    fecha: str | None = None
    secciones: list[ProposalSection] = Field(default_factory=list)
    economica: QuoteDraft


# ── Boilerplate (texto fijo de CiiSA) ─────────────────────────────────────────────

CIISA_ABOUT = (
    "Con oficinas centrales en Monterrey, Nuevo León, Consultoría Integral de "
    "Informática S. A. P. I. de C. V. (CiiSA) tiene como misión, desde su fundación en "
    "1991, el desarrollo de soluciones de negocio para el comercio, industria y el "
    "sector público mediante la aplicación de tecnologías de información, recursos "
    "humanos y manufactura, buscando la simplificación, automatización e integración de "
    "los procesos, aplicando avanzadas metodologías de desarrollo a través de personal "
    "con amplia experiencia en el medio así como con un alta responsabilidad, servicio "
    "al cliente y calidad.\n"
    "Nuestra visión es ser una empresa global, líder en crear soluciones de alto valor "
    "agregado que integren tecnologías, conocimientos y servicios para que nuestros "
    "clientes sean exitosos.\n"
    "Para lograr esta visión, la empresa cuenta con áreas definidas de negocio que "
    "cubren un amplio rango de tecnologías para apoyar a nuestros clientes en el "
    "desarrollo de sus proyectos:\n"
    "- Soluciones y Servicios Adobe\n"
    "- Infraestructura de hardware y software\n"
    "- Soluciones empresariales\n"
    "- Soluciones y Servicios IBM Máximo para mantenimiento y gestión de activos "
    "estratégicos.\n"
    "- Soluciones y Servicios Autodesk\n"
    "- Ingeniería de Software, Redes y Soporte Técnico\n"
    "CiiSA cuenta con:\n"
    "- Consultores Sénior con más de 30 años de experiencia en administración de "
    "proyectos informáticos y con reconocimiento Nacional.\n"
    "- Más de 30 años de experiencia en desarrollos con Multi plataformas y Multi capas.\n"
    "- Más de 30 años de experiencia en integración de soluciones de TI.\n"
    "- Desarrollo de tecnologías emergentes.\n"
    "- Personal con amplia capacidad y experiencia en soporte técnico y conectividad."
)


def confidentiality_text(cliente: str) -> str:
    """Cláusula de confidencialidad + de propiedad, con el nombre del cliente."""
    c = cliente or "el Cliente"
    return (
        f"CiiSA se obliga a guardar estricta confidencialidad sobre los elementos e "
        f"información que proporcione {c}, así como sobre las operaciones que realizan "
        f"para la generación de esta propuesta. Lo anterior, en el entendido de que la "
        f"información proporcionada por {c} es clasificada por {c} como confidencial. "
        f"Por lo anterior CiiSA, así como sus apoderados, empleados y/o funcionarios de "
        f"cualquier clase, no podrán utilizar o divulgar la información sin la "
        f"autorización expresa y por escrito de {c} con un fin diferente al "
        f"anteriormente especificado.\n"
        f"CiiSA no se encuentra obligado a cumplir con la confidencialidad de la "
        f"información proporcionada por {c}, en el caso de que una autoridad "
        f"administrativa competente o judicial le requiera la información confidencial "
        f"proporcionada, o bien que esta información ya sea conocida con anterioridad a "
        f"la fecha de presentación de esta propuesta por CiiSA, o la información sea del "
        f"dominio público.\n\n"
        f"De Propiedad.\n"
        f"CiiSA proporciona esta propuesta de servicios a {c} con propósitos de "
        f"evaluación, por lo que éste último se encuentra obligado a guardar estricta "
        f"confidencialidad sobre todos los elementos e información que ésta contenga, ya "
        f"que estos conjuntos de elementos constituyen un secreto de marca y/o "
        f"información comercial o financiera que está clasificada como confidencial.\n"
        f"Por lo anterior {c}, así como sus representantes legales, empleados y/o "
        f"funcionarios de cualquier clase, no podrán utilizar o divulgar la información "
        f"sin la autorización expresa y por escrito de CiiSA con un fin diferente al "
        f"anteriormente especificado.\n"
        f"En caso de la adjudicación de los servicios aquí propuestos, {c} tendrá la "
        f"propiedad de todos los productos especificados en esta propuesta y derivados "
        f"del desarrollo del proyecto. Sin embargo, lo anterior no incluye la propiedad "
        f"de la(s) metodología(s) y herramientas auxiliares utilizadas por CiiSA para su "
        f"ejecución."
    )


def commercial_terms(economica: QuoteDraft, fecha: str) -> str:
    """Condiciones comerciales DETERMINÍSTICAS, coherentes con la económica.

    Se arma en código (no LLM) para garantizar consistencia: moneda y tratamiento de
    IVA tomados de la tabla económica, y vigencia relativa a la fecha de la propuesta
    (evita copiar fechas stale del precedente)."""
    moneda = economica.moneda or "moneda nacional (MXN)"
    if (economica.impuestos or 0) > 0:
        iva = "Los precios no incluyen IVA; el total refleja el IVA del 16%."
    else:
        iva = "Los precios no incluyen IVA."
    return (
        f"- Precios expresados en {moneda}.\n"
        f"- {iva}\n"
        f"- Vigencia de la propuesta: 30 días naturales a partir de la fecha de "
        f"presentación ({fecha}).\n"
        f"- Forma de pago: según acuerdo comercial; facturación emitida por CiiSA.\n"
        f"- La presente propuesta invalida cualquier versión anterior respecto a los "
        f"servicios y productos cotizados.\n"
        f"- Cualquier modificación en el alcance representará un ajuste en la cotización."
    )


# ── Generación de las secciones narrativas (LLM) ──────────────────────────────────

_SECTIONS_SYSTEM = (
    "Eres un consultor de CiiSA que redacta propuestas técnico-económicas de TI.\n"
    "Te paso una PROPUESTA PRECEDENTE (similar) y el PEDIDO del nuevo cliente. Redactá "
    "las secciones de la NUEVA propuesta, adaptando el precedente al pedido (cliente, "
    "alcance, cantidades).\n"
    "Devolvé ÚNICAMENTE un objeto JSON con EXACTAMENTE estas claves (cada valor es texto; "
    'podés usar viñetas con "- " y saltos de línea):\n'
    '{"objetivo": string, "alcances": string, "limitantes": string, "terminos": string}\n'
    "Guía:\n"
    '- "objetivo": objetivo y antecedentes del proyecto para el cliente del pedido.\n'
    '- "alcances": los alcances técnicos / servicios incluidos, reusando los del '
    "precedente y ajustándolos al pedido.\n"
    '- "limitantes": limitantes y lo NO incluido.\n'
    '- "terminos": términos y condiciones del servicio (horarios, tiempos de respuesta, '
    "responsabilidades). NO incluyas vigencia de la propuesta, precios, IVA ni formas de "
    "pago: eso va en otra sección.\n"
    "Reglas: NO copies fechas absolutas ni vigencias del precedente. NO inventes precios. "
    "Mantené el tono profesional y formal de CiiSA. No incluyas nada fuera del JSON."
)


class _SectionsLLM(BaseModel):
    objetivo: str | None = None
    alcances: str | None = None
    limitantes: str | None = None
    terminos: str | None = None


async def _generate_sections(precedent: str, request: str) -> _SectionsLLM:
    """Llama al LLM para redactar las secciones narrativas desde el precedente."""
    llm = get_chat_llm(streaming=False, temperature=0.2, max_tokens=4096)
    messages = [
        SystemMessage(content=_SECTIONS_SYSTEM),
        HumanMessage(
            content=(
                f"PEDIDO DEL USUARIO:\n{request}\n\n"
                f"PROPUESTA PRECEDENTE (usá como plantilla):\n{precedent}"
            )
        ),
    ]
    response = await llm.ainvoke(messages)
    content = (
        response.content if isinstance(response.content, str) else str(response.content)
    )
    return _SectionsLLM.model_validate(_parse_json(content))


async def build_proposal(*, precedent: str, request: str, fecha: str) -> ProposalDraft:
    """Arma la propuesta completa: boilerplate fijo + secciones LLM + económica.

    Corre en paralelo las dos llamadas al LLM (económica y secciones narrativas) y
    ensambla todo en orden."""
    economica, narr = await asyncio.gather(
        draft_from_precedent(precedent, request),
        _generate_sections(precedent, request),
    )
    # Quitar ítems "placeholder" que el LLM dejó con cantidad 0 (modelos no pedidos).
    economica.items = [it for it in economica.items if (it.cantidad or 0) > 0]
    cliente = (economica.cliente or "").strip() or None

    secciones = [
        ProposalSection(key="acerca", titulo="Acerca de CiiSA", contenido=CIISA_ABOUT, fuente="fijo"),
        ProposalSection(
            key="confidencialidad",
            titulo="Cláusula de confidencialidad",
            contenido=confidentiality_text(cliente or "el Cliente"),
            fuente="fijo",
        ),
        ProposalSection(key="objetivo", titulo="Objetivo", contenido=narr.objetivo or "", fuente="generado"),
        ProposalSection(key="alcances", titulo="Alcances", contenido=narr.alcances or "", fuente="generado"),
        ProposalSection(
            key="limitantes", titulo="Limitantes y no incluido",
            contenido=narr.limitantes or "", fuente="generado",
        ),
        ProposalSection(
            key="terminos", titulo="Términos y condiciones",
            contenido=narr.terminos or "", fuente="generado",
        ),
        # La económica se renderiza acá (la tabla) — placeholder de posición.
        ProposalSection(key="economica", titulo="Propuesta económica", contenido="", fuente="generado"),
        ProposalSection(
            key="condiciones_comerciales", titulo="Condiciones comerciales",
            contenido=commercial_terms(economica, fecha), fuente="fijo",
        ),
    ]
    return ProposalDraft(cliente=cliente, fecha=fecha, secciones=secciones, economica=economica)
