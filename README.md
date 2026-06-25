# 🎲 Sorteo de Grupos

Aplicación en **Streamlit** para sortear grupos al azar a partir de un archivo
`.xlsx` (por ejemplo, las respuestas de un formulario de Google), asignar un
puntaje de desempeño a cada grupo y llevar un historial de los sorteos por fecha.

---

## ✨ Qué hace

- **Panel de administrador** (barra lateral, protegido con contraseña): cargar el
  archivo, configurar y sortear los grupos, editar quién está en cada grupo,
  cargar puntajes, guardar el sorteo en el historial y exportar los resultados.
- **Pantalla principal** (visible para todos, ideal para proyectar): muestra el
  nombre de la actividad con su fecha, los grupos con su puntaje, la animación
  del armado y el historial de sorteos anteriores.
- **Persistencia**: todo se guarda en `sorteo_data.json`, así los grupos, los
  puntajes y el historial se conservan aunque cierres y vuelvas a abrir la app.
- **Exportación**: los resultados (nombre y apellido · grupo · puntaje) se pueden
  copiar y pegar directamente en Excel o Google Sheets, o descargar como CSV.

---

## 📁 Estructura del proyecto

```
Organizar grupos/
├── sorteo_grupos.py          # La aplicación
├── requirements.txt          # Dependencias
├── README.md                 # Este archivo
├── sorteo_data.json          # Se crea solo al usar la app (datos guardados)
└── .streamlit/
    ├── secrets.toml          # Contraseña de administrador (no compartir)
    └── config.toml           # Tema y opciones de Streamlit
```

> El archivo `sorteo_data.json` se genera automáticamente la primera vez que
> sorteás grupos. No hace falta crearlo a mano.

---

## 🔧 Instalación

Requiere **Python 3.9 o superior**. Desde la carpeta del proyecto:

```bash
python -m pip install -r requirements.txt
```

> En Windows, usá siempre `python -m pip ...` y `python -m streamlit ...`
> (con el prefijo `python -m`) para asegurarte de que `pip` y `streamlit`
> usen el mismo Python. Si tenés `python3`, reemplazá `python` por `python3`.

---

## ▶️ Cómo ejecutar

```bash
python -m streamlit run sorteo_grupos.py
```

Se abre en el navegador, normalmente en `http://localhost:8501`.

---

## 🔑 Contraseña de administrador

La contraseña se define en `.streamlit/secrets.toml`:

```toml
admin_password = "cambiame_por_una_clave_segura"
```

Cambiá ese valor por una contraseña propia. Si el archivo no existe o no se
puede leer, la app usa la contraseña por defecto `admin123`.

**No subas `secrets.toml` a un repositorio público.** Si usás Git, agregalo a
tu `.gitignore`.

---

## 📊 Formato del archivo Excel

El archivo `.xlsx` puede tener todas las columnas que quieras (las del
formulario de Google), pero **debe incluir una columna llamada
`nombre y apellido`**. La app la detecta sin importar mayúsculas ni espacios
de más. Las demás columnas se ignoran.

| nombre y apellido | correo            | curso |
|-------------------|-------------------|-------|
| Ana Pérez         | ana@ejemplo.com   | 5°A   |
| Juan Gómez        | juan@ejemplo.com  | 5°A   |

---

## 🧭 Cómo usarla

1. **Iniciá sesión** en el panel de administrador (barra lateral) con tu contraseña.
2. **Cargá el archivo** `.xlsx`.
3. Escribí el **nombre de la actividad** y elegí cómo armar los grupos: por
   *cantidad de grupos* o por *personas por grupo*.
4. Apretá **🎲 Sortear grupos**. En la pantalla principal vas a ver cómo se
   arman los grupos y, al final, la animación de globos.
5. Si hace falta, **editá los integrantes** (mover un alumno de un grupo a otro)
   y **cargá los puntajes** de cada grupo. Todo se refleja en la pantalla principal.
6. **Guardá en el historial** para conservar el sorteo con su fecha.
7. **Exportá** los resultados para pegarlos en tu planilla de notas.

> Quien abra la app sin iniciar sesión verá la pantalla principal (grupos,
> puntajes e historial), pero no podrá modificar nada. Ideal para proyectar.

---

## ⚙️ Personalización rápida (en `sorteo_grupos.py`)

- `REVEAL_DELAY` — velocidad de la animación del armado (más alto = más lento).
- `NAME_COLUMN` — nombre exacto de la columna de alumnos.
- `PALETTE` — colores de las tarjetas de cada grupo.

> Nota: la animación de globos de Streamlit (`st.balloons`) tiene una velocidad
> fija que no se puede cambiar; lo que sí se ajusta es la animación del armado
> de los grupos mediante `REVEAL_DELAY`.

---

## 🛟 Problemas frecuentes

- **`Missing optional dependency 'openpyxl'`**: instalá las dependencias en el
  mismo Python que usa Streamlit con `python -m pip install -r requirements.txt`
  y ejecutá la app con `python -m streamlit run sorteo_grupos.py`.
- **La contraseña no funciona**: revisá que `.streamlit/secrets.toml` esté en la
  carpeta correcta y que reiniciaste la app después de editarlo.
