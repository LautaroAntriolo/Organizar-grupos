"""
Sorteo de Grupos — App de Streamlit
=====================================

Permite a un docente (administrador) cargar un archivo .xlsx con los alumnos,
sortear grupos al azar mostrando la animación del armado, asignar un puntaje a
cada grupo y exportar el resultado (nombre y apellido + grupo + puntaje) en un
formato listo para copiar y pegar en una hoja de cálculo.

Cómo ejecutar
-------------
1) Instalar dependencias:
       pip install streamlit pandas openpyxl
2) Ejecutar:
       streamlit run sorteo_grupos.py
3) Abrir el navegador en la URL que muestra la terminal (normalmente
   http://localhost:8501).

Contraseña de administrador
---------------------------
Por defecto es "admin123". Para cambiarla de forma segura, creá el archivo
.streamlit/secrets.toml junto a este script con el contenido:
       admin_password = "tu_clave_secreta"
Si no existe ese archivo, se usa la contraseña por defecto definida abajo.
"""

import html
import random

import pandas as pd
import streamlit as st

# --------------------------------------------------------------------------- #
# Configuración general
# --------------------------------------------------------------------------- #
st.set_page_config(page_title="Sorteo de Grupos", page_icon="🎲", layout="wide")

NAME_COLUMN = "nombre y apellido"          # Columna que se usa del Excel
DEFAULT_PASSWORD = "admin123"              # Clave por defecto (cambiar por secrets)
PALETTE = ["#6366f1", "#ec4899", "#f59e0b", "#10b981",
           "#3b82f6", "#ef4444", "#8b5cf6", "#14b8a6"]


def get_admin_password() -> str:
    """Devuelve la clave desde secrets.toml o la clave por defecto."""
    try:
        return st.secrets["admin_password"]
    except Exception:
        return DEFAULT_PASSWORD


# --------------------------------------------------------------------------- #
# Estado de la sesión
# --------------------------------------------------------------------------- #
def init_state() -> None:
    defaults = {
        "authenticated": False,   # ¿Hay un admin logueado?
        "students": [],           # Lista de nombres cargados
        "groups": [],             # Lista de grupos (cada uno es una lista de nombres)
        "source_file": None,      # Nombre del archivo cargado
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


init_state()


# --------------------------------------------------------------------------- #
# Estilos
# --------------------------------------------------------------------------- #
st.markdown(
    """
    <style>
    .group-grid { display:flex; flex-wrap:wrap; gap:18px; margin-top:10px; }
    .group-card {
        flex:1 1 240px; min-width:220px; border-radius:16px;
        padding:18px 20px; background:rgba(255,255,255,0.04);
        border:1px solid rgba(255,255,255,0.08);
        border-left:6px solid var(--accent, #6366f1);
        box-shadow:0 4px 16px rgba(0,0,0,0.12);
    }
    .group-title { font-weight:700; font-size:1.1rem; margin-bottom:10px;
                   color:var(--accent, #6366f1); }
    .group-members { list-style:none; padding:0; margin:0; }
    .group-members li { padding:7px 2px; font-size:0.98rem;
                        border-bottom:1px dashed rgba(255,255,255,0.10); }
    .group-members li:last-child { border-bottom:none; }
    .group-score { margin-top:10px; font-weight:600; font-size:0.95rem;
                   opacity:0.85; }
    .empty-slot { opacity:0.25; font-style:italic; }
    </style>
    """,
    unsafe_allow_html=True,
)


# --------------------------------------------------------------------------- #
# Lógica de sorteo
# --------------------------------------------------------------------------- #
def find_name_column(df: pd.DataFrame):
    """Busca la columna 'nombre y apellido' sin distinguir mayúsculas/espacios."""
    target = NAME_COLUMN.strip().lower()
    for col in df.columns:
        if str(col).strip().lower() == target:
            return col
    return None


def clean_names(series: pd.Series) -> list:
    """Limpia la columna: descarta vacíos y espacios sobrantes."""
    names = (
        series.dropna()
        .astype(str)
        .map(str.strip)
    )
    return [n for n in names if n]


def make_groups_by_count(students: list, n_groups: int) -> list:
    """Reparte a los alumnos en n_groups grupos lo más parejos posible."""
    shuffled = students[:]
    random.shuffle(shuffled)
    groups = [[] for _ in range(n_groups)]
    for i, name in enumerate(shuffled):
        groups[i % n_groups].append(name)
    return groups


def make_groups_by_size(students: list, size: int) -> list:
    """Arma grupos de 'size' personas (el último puede quedar más chico)."""
    shuffled = students[:]
    random.shuffle(shuffled)
    return [shuffled[i:i + size] for i in range(0, len(shuffled), size)]


# --------------------------------------------------------------------------- #
# Render de grupos
# --------------------------------------------------------------------------- #
def group_card_html(index: int, members: list, total_slots: int = None,
                    score=None) -> str:
    """Devuelve el HTML de una tarjeta de grupo."""
    accent = PALETTE[index % len(PALETTE)]
    items = "".join(f"<li>{html.escape(m)}</li>" for m in members)
    # Espacios vacíos para la animación (ranuras todavía no reveladas)
    if total_slots:
        for _ in range(total_slots - len(members)):
            items += "<li class='empty-slot'>…</li>"
    score_html = (
        f"<div class='group-score'>Puntaje: {score}</div>"
        if score not in (None, "") else ""
    )
    return (
        f"<div class='group-card' style='--accent:{accent}'>"
        f"<div class='group-title'>Grupo {index + 1}</div>"
        f"<ul class='group-members'>{items}</ul>"
        f"{score_html}</div>"
    )


def groups_grid_html(groups: list, slots: list = None) -> str:
    cards = []
    for i, g in enumerate(groups):
        total = slots[i] if slots else None
        cards.append(group_card_html(i, g, total_slots=total))
    return f"<div class='group-grid'>{''.join(cards)}</div>"


def animate_groups(final_groups: list) -> None:
    """Muestra el armado de los grupos revelando un nombre por vez."""
    import time

    slots = [len(g) for g in final_groups]
    revealed = [[] for _ in final_groups]
    placeholder = st.empty()
    max_len = max(slots) if slots else 0

    for pos in range(max_len):
        for gi, group in enumerate(final_groups):
            if pos < len(group):
                revealed[gi].append(group[pos])
                placeholder.markdown(
                    groups_grid_html(revealed, slots=slots),
                    unsafe_allow_html=True,
                )
                time.sleep(0.18)
    # Render final estable
    placeholder.markdown(groups_grid_html(final_groups), unsafe_allow_html=True)


# --------------------------------------------------------------------------- #
# Exportación
# --------------------------------------------------------------------------- #
def build_export_df() -> pd.DataFrame:
    rows = []
    for gi, group in enumerate(st.session_state.groups):
        score = st.session_state.get(f"score_{gi}", "")
        for member in group:
            rows.append(
                {"nombre y apellido": member,
                 "grupo": f"Grupo {gi + 1}",
                 "puntaje": score}
            )
    return pd.DataFrame(rows, columns=["nombre y apellido", "grupo", "puntaje"])


def clear_score_keys() -> None:
    for key in [k for k in st.session_state.keys() if k.startswith("score_")]:
        del st.session_state[key]


# --------------------------------------------------------------------------- #
# Barra lateral: login de administrador
# --------------------------------------------------------------------------- #
with st.sidebar:
    st.header("🔐 Administrador")
    if st.session_state.authenticated:
        st.success("Sesión iniciada como administrador.")
        if st.button("Cerrar sesión"):
            st.session_state.authenticated = False
            st.rerun()
    else:
        pwd = st.text_input("Contraseña", type="password")
        if st.button("Ingresar"):
            if pwd == get_admin_password():
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Contraseña incorrecta.")
        st.caption("Solo el administrador puede cargar archivos y asignar "
                   "puntajes. Los grupos sorteados se ven en pantalla "
                   "aunque no haya sesión iniciada.")


# --------------------------------------------------------------------------- #
# Vista pública (sin sesión de admin)
# --------------------------------------------------------------------------- #
st.title("🎲 Sorteo de Grupos")

if not st.session_state.authenticated:
    if st.session_state.groups:
        st.subheader("Resultado del sorteo")
        st.markdown(groups_grid_html(st.session_state.groups),
                    unsafe_allow_html=True)
    else:
        st.info("El sorteo todavía no se realizó. "
                "El administrador debe iniciar sesión para cargarlo.")
    st.stop()


# --------------------------------------------------------------------------- #
# Vista de administrador
# --------------------------------------------------------------------------- #
# 1) Carga del archivo ------------------------------------------------------- #
st.subheader("1) Cargar lista de alumnos")
uploaded = st.file_uploader(
    "Subí el archivo .xlsx del formulario de Google",
    type=["xlsx"],
)

if uploaded is not None:
    try:
        df = pd.read_excel(uploaded)
    except Exception as exc:  # noqa: BLE001
        st.error(f"No se pudo leer el archivo: {exc}")
        st.stop()

    col = find_name_column(df)
    if col is None:
        st.error(
            f"No encontré la columna «{NAME_COLUMN}». "
            f"Columnas disponibles: {', '.join(map(str, df.columns))}."
        )
        st.stop()

    names = clean_names(df[col])
    if not names:
        st.error("La columna de nombres está vacía.")
        st.stop()

    # Si cambió el archivo, reseteamos el sorteo previo
    if st.session_state.source_file != uploaded.name:
        st.session_state.students = names
        st.session_state.groups = []
        clear_score_keys()
        st.session_state.source_file = uploaded.name

    st.success(f"Se cargaron {len(names)} alumnos desde «{uploaded.name}».")
    with st.expander("Ver alumnos cargados"):
        st.write(names)

# 2) Configuración del sorteo ----------------------------------------------- #
if st.session_state.students:
    total = len(st.session_state.students)
    st.subheader("2) Configurar el sorteo")

    mode = st.radio(
        "¿Cómo querés armar los grupos?",
        ["Por cantidad de grupos", "Por personas por grupo"],
        horizontal=True,
    )

    if mode == "Por cantidad de grupos":
        n_groups = st.number_input(
            "Cantidad de grupos", min_value=1, max_value=total,
            value=min(4, total), step=1,
        )
        config = ("count", int(n_groups))
    else:
        size = st.number_input(
            "Personas por grupo", min_value=1, max_value=total,
            value=min(4, total), step=1,
        )
        config = ("size", int(size))

    col_a, col_b = st.columns([1, 1])
    with col_a:
        sortear = st.button("🎲 Sortear grupos", type="primary",
                            use_container_width=True)
    with col_b:
        reset = st.button("↺ Reiniciar sorteo", use_container_width=True)

    if reset:
        st.session_state.groups = []
        clear_score_keys()
        st.rerun()

    # 3) Sorteo + animación -------------------------------------------------- #
    if sortear:
        if config[0] == "count":
            groups = make_groups_by_count(st.session_state.students, config[1])
        else:
            groups = make_groups_by_size(st.session_state.students, config[1])

        clear_score_keys()
        st.session_state.groups = groups

        st.subheader("Armando los grupos…")
        animate_groups(groups)
        st.balloons()

# 4) Grupos + puntajes ------------------------------------------------------- #
if st.session_state.groups:
    st.divider()
    st.subheader("3) Grupos y puntajes")
    st.caption("Asigná el puntaje de desempeño a cada grupo. "
               "Se guarda automáticamente.")

    groups = st.session_state.groups
    per_row = 3
    for start in range(0, len(groups), per_row):
        cols = st.columns(per_row)
        for offset, gi in enumerate(range(start, min(start + per_row, len(groups)))):
            with cols[offset]:
                with st.container(border=True):
                    st.markdown(f"**Grupo {gi + 1}**")
                    for member in groups[gi]:
                        st.write(f"• {member}")
                    st.number_input(
                        "Puntaje", min_value=0.0, step=1.0,
                        key=f"score_{gi}",
                    )

    # 5) Exportación --------------------------------------------------------- #
    st.divider()
    st.subheader("4) Exportar resultados")

    export_df = build_export_df()
    tsv = export_df.to_csv(sep="\t", index=False)
    csv = export_df.to_csv(index=False)

    st.markdown("**Copiar y pegar en una hoja de cálculo** "
                "(seleccioná todo el texto y pegalo en Excel o Google Sheets):")
    st.text_area("Datos (separados por tabulaciones)", tsv, height=240)

    st.download_button(
        "⬇️ Descargar como CSV",
        data=csv.encode("utf-8-sig"),
        file_name="puntajes_grupos.csv",
        mime="text/csv",
    )
