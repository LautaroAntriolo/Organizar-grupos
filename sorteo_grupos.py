"""
Sorteo de Grupos — App de Streamlit
=====================================

Estructura de la pantalla:
- PANEL DE ADMINISTRADOR (barra lateral): login + carga del .xlsx + control del
  sorteo (configurar, sortear, editar integrantes, cargar puntajes, guardar en
  historial y exportar).
- PANTALLA PRINCIPAL (área central, visible para todos): muestra la actividad y
  su fecha, los grupos sorteados con su puntaje, la animación del armado y el
  historial de sorteos anteriores por fecha.

Los datos se guardan en "sorteo_data.json" (junto a este archivo), así el
resultado y el historial se conservan entre sesiones y reinicios de la app.

Cómo ejecutar
-------------
    python -m pip install -r requirements.txt
    python -m streamlit run sorteo_grupos.py

La contraseña por defecto es "admin123". Para cambiarla, editá
.streamlit/secrets.toml (clave admin_password).
"""

import html
import json
import os
import random
import time
from datetime import datetime

import pandas as pd
import streamlit as st

# --------------------------------------------------------------------------- #
# Configuración general
# --------------------------------------------------------------------------- #
st.set_page_config(page_title="Sorteo de Grupos", page_icon="🎲", layout="wide")

NAME_COLUMN = "nombre y apellido"          # Columna que se usa del Excel
DEFAULT_PASSWORD = "admin123"              # Clave por defecto (cambiar por secrets)
REVEAL_DELAY = 0.45                        # Velocidad de la animación (más alto = más lento)
PALETTE = ["#6366f1", "#ec4899", "#f59e0b", "#10b981",
           "#3b82f6", "#ef4444", "#8b5cf6", "#14b8a6"]
DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "sorteo_data.json")


def get_admin_password() -> str:
    try:
        return st.secrets["admin_password"]
    except Exception:
        return DEFAULT_PASSWORD


# --------------------------------------------------------------------------- #
# Persistencia en archivo JSON
# --------------------------------------------------------------------------- #
def default_data() -> dict:
    return {"students": [], "current": None, "history": []}


def load_data() -> dict:
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, encoding="utf-8") as fh:
                d = json.load(fh)
                for key, val in default_data().items():
                    d.setdefault(key, val)
                return d
        except Exception:
            return default_data()
    return default_data()


def save_data(data: dict) -> None:
    with open(DATA_FILE, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)


# --------------------------------------------------------------------------- #
# Estado de sesión (solo cosas transitorias) + carga de datos
# --------------------------------------------------------------------------- #
st.session_state.setdefault("authenticated", False)
st.session_state.setdefault("just_drawn", False)

data = load_data()


# --------------------------------------------------------------------------- #
# Estilos
# --------------------------------------------------------------------------- #
st.markdown(
    """
    <style>
    [data-testid="stSidebar"] { min-width: 350px; }
    .activity-card {
        border-radius:18px; padding:18px 24px; margin:4px 0 18px;
        background:linear-gradient(135deg, rgba(99,102,241,0.20),
                                            rgba(236,72,153,0.14));
        border:1px solid rgba(255,255,255,0.12);
    }
    .activity-name { font-size:1.7rem; font-weight:800; line-height:1.2; }
    .activity-date { opacity:0.8; margin-top:4px; font-size:0.95rem; }
    .group-grid { display:flex; flex-wrap:wrap; gap:18px; margin-top:6px; }
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
    .group-score { margin-top:12px; font-weight:700; font-size:1rem; }
    .empty-slot { opacity:0.25; font-style:italic; }
    </style>
    """,
    unsafe_allow_html=True,
)


# --------------------------------------------------------------------------- #
# Utilidades de datos
# --------------------------------------------------------------------------- #
def find_name_column(df: pd.DataFrame):
    target = NAME_COLUMN.strip().lower()
    for col in df.columns:
        if str(col).strip().lower() == target:
            return col
    return None


def clean_names(series: pd.Series) -> list:
    names = series.dropna().astype(str).map(str.strip)
    return [n for n in names if n]


def make_groups_by_count(students: list, n_groups: int) -> list:
    shuffled = students[:]
    random.shuffle(shuffled)
    groups = [[] for _ in range(n_groups)]
    for i, name in enumerate(shuffled):
        groups[i % n_groups].append(name)
    return groups


def make_groups_by_size(students: list, size: int) -> list:
    shuffled = students[:]
    random.shuffle(shuffled)
    return [shuffled[i:i + size] for i in range(0, len(shuffled), size)]


def fmt_score(value) -> str:
    if value is None or value == "":
        return ""
    try:
        f = float(value)
        return str(int(f)) if f == int(f) else f"{f:g}"
    except (TypeError, ValueError):
        return str(value)


def clear_score_keys() -> None:
    for key in [k for k in list(st.session_state.keys())
                if k.startswith("score_")]:
        del st.session_state[key]


def build_export_df(current: dict) -> pd.DataFrame:
    rows = []
    scores = current.get("scores", {})
    for gi, group in enumerate(current["groups"]):
        sc = fmt_score(scores.get(str(gi), ""))
        for member in group:
            rows.append({"nombre y apellido": member,
                         "grupo": f"Grupo {gi + 1}",
                         "puntaje": sc})
    return pd.DataFrame(rows, columns=["nombre y apellido", "grupo", "puntaje"])


# --------------------------------------------------------------------------- #
# Render (HTML) de tarjetas
# --------------------------------------------------------------------------- #
def activity_card_html(activity: str, date: str) -> str:
    name = html.escape(activity) if activity else "Actividad sin nombre"
    return (
        "<div class='activity-card'>"
        f"<div class='activity-name'>📋 {name}</div>"
        f"<div class='activity-date'>📅 {html.escape(date)}</div>"
        "</div>"
    )


def group_card_html(index: int, members: list, total_slots: int = None,
                    score=None) -> str:
    accent = PALETTE[index % len(PALETTE)]
    items = "".join(f"<li>{html.escape(str(m))}</li>" for m in members)
    if total_slots:
        for _ in range(total_slots - len(members)):
            items += "<li class='empty-slot'>…</li>"
    score_html = ""
    if score is not None and fmt_score(score) != "":
        score_html = (f"<div class='group-score' style='color:{accent}'>"
                      f"🏆 Puntaje: {fmt_score(score)}</div>")
    return (f"<div class='group-card' style='--accent:{accent}'>"
            f"<div class='group-title'>Grupo {index + 1}</div>"
            f"<ul class='group-members'>{items}</ul>{score_html}</div>")


def groups_grid_html(groups: list, slots: list = None, scores: dict = None) -> str:
    scores = scores or {}
    cards = []
    for i, group in enumerate(groups):
        total = slots[i] if slots else None
        cards.append(group_card_html(i, group, total_slots=total,
                                     score=scores.get(str(i))))
    return f"<div class='group-grid'>{''.join(cards)}</div>"


def animate_groups(groups: list, scores: dict) -> None:
    slots = [len(g) for g in groups]
    revealed = [[] for _ in groups]
    placeholder = st.empty()
    max_len = max(slots) if slots else 0
    for pos in range(max_len):
        for gi, group in enumerate(groups):
            if pos < len(group):
                revealed[gi].append(group[pos])
                placeholder.markdown(
                    groups_grid_html(revealed, slots=slots),
                    unsafe_allow_html=True,
                )
                time.sleep(REVEAL_DELAY)
    placeholder.markdown(groups_grid_html(groups, scores=scores),
                         unsafe_allow_html=True)


# =========================================================================== #
# PANEL DE ADMINISTRADOR (barra lateral)
# =========================================================================== #
with st.sidebar:
    st.header("🔐 Panel de administrador")

    if not st.session_state.authenticated:
        pwd = st.text_input("Contraseña", type="password")
        if st.button("Ingresar", use_container_width=True):
            if pwd == get_admin_password():
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Contraseña incorrecta.")
        st.caption("La pantalla principal muestra los grupos, sus puntajes y el "
                   "historial. Iniciá sesión para cargar datos y administrar.")
    else:
        top_a, top_b = st.columns([2, 1])
        top_a.success("Sesión iniciada")
        if top_b.button("Salir"):
            st.session_state.authenticated = False
            st.rerun()

        # --- 1) Carga de datos --------------------------------------------- #
        st.markdown("### 📁 Cargar alumnos")
        uploaded = st.file_uploader("Archivo .xlsx del formulario", type=["xlsx"])
        if uploaded is not None:
            try:
                df = pd.read_excel(uploaded)
            except Exception as exc:  # noqa: BLE001
                st.error(f"No se pudo leer el archivo: {exc}")
            else:
                col = find_name_column(df)
                if col is None:
                    st.error(
                        f"No encontré la columna «{NAME_COLUMN}». "
                        f"Columnas: {', '.join(map(str, df.columns))}."
                    )
                else:
                    names = clean_names(df[col])
                    if names and names != data["students"]:
                        data["students"] = names
                        save_data(data)
                    if names:
                        st.success(f"{len(names)} alumnos cargados.")

        # --- 2) Configurar y sortear --------------------------------------- #
        if data["students"]:
            total = len(data["students"])
            st.caption(f"👥 {total} alumnos en la lista.")
            st.markdown("### 🎲 Nuevo sorteo")

            activity_default = (data["current"]["activity"]
                                if data.get("current") else "")
            activity = st.text_input("Nombre de la actividad",
                                     value=activity_default, key="activity_input")

            mode = st.radio("Armar grupos por:",
                            ["Cantidad de grupos", "Personas por grupo"])
            if mode == "Cantidad de grupos":
                amount = st.number_input("Cantidad de grupos", 1, total,
                                         min(4, total), step=1)
                config = ("count", int(amount))
            else:
                amount = st.number_input("Personas por grupo", 1, total,
                                         min(4, total), step=1)
                config = ("size", int(amount))

            if st.button("🎲 Sortear grupos", type="primary",
                         use_container_width=True):
                if config[0] == "count":
                    groups = make_groups_by_count(data["students"], config[1])
                else:
                    groups = make_groups_by_size(data["students"], config[1])
                clear_score_keys()
                data["current"] = {
                    "activity": activity.strip(),
                    "date": datetime.now().strftime("%d/%m/%Y %H:%M"),
                    "groups": groups,
                    "scores": {str(i): 0 for i in range(len(groups))},
                }
                save_data(data)
                st.session_state.just_drawn = True
                st.rerun()

        # --- 3) Administrar el sorteo actual ------------------------------- #
        current = data.get("current")
        if current and current.get("groups"):
            ngroups = len(current["groups"])
            st.divider()
            st.markdown("### ⚙️ Sorteo actual")

            with st.expander("📝 Renombrar actividad"):
                new_name = st.text_input("Nombre", value=current["activity"],
                                         key="rename_input")
                if st.button("Actualizar nombre"):
                    data["current"]["activity"] = new_name.strip()
                    save_data(data)
                    st.rerun()

            with st.expander("✏️ Editar integrantes"):
                st.caption("Mové un alumno de un grupo a otro.")
                all_students = [m for g in current["groups"] for m in g]
                if all_students:
                    who = st.selectbox("Alumno", all_students, key="mv_student")
                    dest = st.selectbox(
                        "Mover al…",
                        [f"Grupo {i + 1}" for i in range(ngroups)],
                        key="mv_dest",
                    )
                    if st.button("Mover", key="mv_btn"):
                        dest_idx = int(dest.split()[-1]) - 1
                        new_groups = [[m for m in g if m != who]
                                      for g in current["groups"]]
                        new_groups[dest_idx].append(who)
                        data["current"]["groups"] = new_groups
                        save_data(data)
                        st.rerun()

            with st.expander("🏆 Cargar puntajes"):
                for gi in range(ngroups):
                    skey = f"score_{gi}"
                    if skey not in st.session_state:
                        st.session_state[skey] = float(
                            current["scores"].get(str(gi), 0.0))
                    st.number_input(f"Grupo {gi + 1}", min_value=0.0,
                                    step=1.0, key=skey)
                new_scores = {str(gi): float(st.session_state[f"score_{gi}"])
                              for gi in range(ngroups)}
                old_scores = {k: float(v)
                              for k, v in current.get("scores", {}).items()}
                if new_scores != old_scores:
                    data["current"]["scores"] = new_scores
                    save_data(data)

            with st.expander("💾 Guardar en el historial"):
                st.caption("Guarda una copia del sorteo actual (con su fecha y "
                           "puntajes) en el historial.")
                if st.button("Guardar en historial", use_container_width=True):
                    data["history"].append({
                        "activity": current["activity"],
                        "date": current["date"],
                        "groups": [list(g) for g in current["groups"]],
                        "scores": dict(data["current"]["scores"]),
                    })
                    save_data(data)
                    st.success("Guardado en el historial.")

            with st.expander("⬇️ Exportar (copiar y pegar)"):
                export_df = build_export_df(current)
                tsv = export_df.to_csv(sep="\t", index=False)
                st.text_area("Datos (pegar en Excel / Google Sheets)",
                             tsv, height=200)
                st.download_button(
                    "Descargar CSV",
                    data=export_df.to_csv(index=False).encode("utf-8-sig"),
                    file_name="puntajes_grupos.csv",
                    mime="text/csv",
                )

        # --- Historial (también visible en el panel) ----------------------- #
        if data.get("history"):
            st.divider()
            with st.expander(f"📚 Historial ({len(data['history'])} sorteos)"):
                for entry in reversed(data["history"]):
                    nombre = entry["activity"] or "Sin nombre"
                    st.write(f"📅 {entry['date']} — {nombre}")


# =========================================================================== #
# PANTALLA PRINCIPAL (área central, visible para todos)
# =========================================================================== #
st.title("🎲 Sorteo de Grupos")

current = data.get("current")
if current and current.get("groups"):
    st.markdown(activity_card_html(current["activity"], current["date"]),
                unsafe_allow_html=True)

    if st.session_state.just_drawn:
        st.subheader("Armando los grupos…")
        animate_groups(current["groups"], current.get("scores", {}))
        time.sleep(0.6)
        st.balloons()
        st.session_state.just_drawn = False
    else:
        st.markdown(
            groups_grid_html(current["groups"], scores=current.get("scores", {})),
            unsafe_allow_html=True,
        )
else:
    st.info("Todavía no se realizó ningún sorteo. "
            "El administrador puede iniciar sesión en el panel de la izquierda "
            "para cargar la lista y sortear los grupos.")

# Historial de sorteos por fecha
if data.get("history"):
    st.divider()
    st.subheader("📚 Historial de sorteos")
    for entry in reversed(data["history"]):
        nombre = entry["activity"] or "Sin nombre"
        with st.expander(f"📅 {entry['date']} — {nombre}"):
            st.markdown(
                groups_grid_html(entry["groups"], scores=entry.get("scores", {})),
                unsafe_allow_html=True,
            )
