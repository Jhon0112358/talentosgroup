from flask import Flask, render_template, request
import sqlite3
import os
from datetime import datetime

app = Flask(__name__) 
app.secret_key = 'Admin0112358'  # Puedes cambiarla por algo más complejo


# === Crear base de datos si no existe ===
def crear_base():
    if not os.path.exists("database.db"):
        conn = sqlite3.connect("database.db")
        c = conn.cursor()
        c.execute("""
            CREATE TABLE usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                correo TEXT NOT NULL UNIQUE,
                clave TEXT NOT NULL,
                tipo TEXT NOT NULL
            )
        """)
        conn.commit()
        conn.close()

# === Ruta para registrar usuario ===
@app.route("/registro", methods=["GET", "POST"])
def registro():
    mensaje = ""
    if request.method == "POST":
        nombre = request.form["nombre"]
        correo = request.form["correo"]
        clave = request.form["clave"]
        tipo = request.form["tipo"]

        # Guardar en la base de datos
        try:
            conn = sqlite3.connect("database.db")
            c = conn.cursor()
            c.execute("INSERT INTO usuarios (nombre, correo, clave, tipo) VALUES (?, ?, ?, ?)",
                      (nombre, correo, clave, tipo))
            conn.commit()
            conn.close()
            mensaje = "Usuario registrado exitosamente"
        except sqlite3.IntegrityError:
            mensaje = "¡Ese correo ya está registrado!"

    return render_template("registro.html", mensaje=mensaje)
from flask import session, redirect, url_for

@app.route("/login", methods=["GET", "POST"])
def login():
    mensaje = ""
    if request.method == "POST":
        correo = request.form["correo"]
        clave = request.form["clave"]

        # Buscar usuario en la base de datos
        conn = sqlite3.connect("database.db")
        c = conn.cursor()
        c.execute("SELECT id, nombre, tipo FROM usuarios WHERE correo=? AND clave=?", (correo, clave))
        usuario = c.fetchone()
        conn.close()

        if usuario:
            session["usuario_id"] = usuario[0]
            session["usuario_nombre"] = usuario[1]
            session["usuario_tipo"] = usuario[2]
            return redirect(url_for("panel"))
        else:
            mensaje = "Correo o contraseña incorrectos"

    return render_template("login.html", mensaje=mensaje)
@app.route("/panel")
def panel():
    if "usuario_id" not in session:
        return redirect(url_for("login"))

    enlaces = []

    if session["usuario_tipo"] == "candidato":
        enlaces.append({"url": "/subir_hoja", "texto": "Subir hoja de vida"})
    elif session["usuario_tipo"] == "empresa":
        enlaces.append({"url": "/nueva_oferta", "texto": "Publicar nueva oferta"})

    enlaces.append({"url": "/ofertas", "texto": "Ver ofertas disponibles"})
    enlaces.append({"url": "/logout", "texto": "Cerrar sesión"})

    return render_template("panel.html",
                           nombre=session["usuario_nombre"],
                           tipo=session["usuario_tipo"],
                           enlaces=enlaces)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))
#ruta para subir la hoja de vida en pdf
from werkzeug.utils import secure_filename

@app.route("/subir_hoja", methods=["GET", "POST"])
def subir_hoja():
    if "usuario_id" not in session or session["usuario_tipo"] != "candidato":
        return redirect(url_for("login"))

    mensaje = ""
    if request.method == "POST":
        archivo = request.files["archivo"]
        if archivo and archivo.filename.endswith(".pdf"):
            nombre_archivo = secure_filename(f"{session['usuario_id']}_{archivo.filename}")
            ruta_archivo = os.path.join("static/uploads", nombre_archivo)
            archivo.save(ruta_archivo)

            # Guardar nombre del archivo en la base de datos
            conn = sqlite3.connect("database.db")
            c = conn.cursor()
            c.execute("UPDATE usuarios SET hoja_vida=? WHERE id=?", (nombre_archivo, session["usuario_id"]))
            conn.commit()
            conn.close()

            mensaje = "Hoja de vida subida exitosamente"

    return render_template("subir_hoja.html", mensaje=mensaje)
#ruta para oferta de empleo
@app.route("/nueva_oferta", methods=["GET", "POST"])
def nueva_oferta():
    if "usuario_id" not in session or session["usuario_tipo"] != "empresa":
        return redirect(url_for("login"))

    mensaje = ""
    if request.method == "POST":
        titulo = request.form["titulo"]
        descripcion = request.form["descripcion"]
        empresa = session["usuario_nombre"]
        fecha = datetime.now().strftime("%Y-%m-%d")

        conn = sqlite3.connect("database.db")
        c = conn.cursor()
        c.execute("INSERT INTO ofertas (titulo, descripcion, empresa, fecha) VALUES (?, ?, ?, ?)",
                  (titulo, descripcion, empresa, fecha))
        conn.commit()
        conn.close()

        mensaje = "Oferta publicada exitosamente"
        # Dejar el formulario vacío después de publicar
        return render_template("nueva_oferta.html", mensaje=mensaje)

    return render_template("nueva_oferta.html", mensaje=mensaje)

#ofertas
@app.route("/ofertas", methods=["GET", "POST"])
def ver_ofertas():
    if "usuario_id" not in session:
        return redirect(url_for("login"))

    palabra_clave = request.form.get("busqueda", "").strip()

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    if palabra_clave:
        consulta = """
            SELECT id, titulo, descripcion, empresa, fecha 
            FROM ofertas 
            WHERE titulo LIKE ? OR descripcion LIKE ?
            ORDER BY fecha DESC
        """
        c.execute(consulta, (f"%{palabra_clave}%", f"%{palabra_clave}%"))
    else:
        c.execute("SELECT id, titulo, descripcion, empresa, fecha FROM ofertas ORDER BY fecha DESC")

    ofertas = c.fetchall()
    conn.close()

    return render_template("ofertas.html", ofertas=ofertas, palabra_clave=palabra_clave)

@app.route("/postular/<int:oferta_id>")
def postular(oferta_id):
    if "usuario_id" not in session or session.get("usuario_tipo") != "candidato":
        return redirect(url_for("login"))

    conn = sqlite3.connect("bolsa_empleo.db")
    c = conn.cursor()

    # Verifica si ya postuló
    c.execute("SELECT * FROM postulaciones WHERE oferta_id=? AND candidato_id=?", (oferta_id, session["usuario_id"]))
    if c.fetchone():
        conn.close()
        return "<p>Ya te has postulado a esta oferta.</p><p><a href='/ofertas'>Volver a ofertas</a></p>"

    # Inserta postulación
    fecha_postulacion = datetime.now().strftime("%Y-%m-%d")
    c.execute("INSERT INTO postulaciones (oferta_id, candidato_id, fecha_postulacion) VALUES (?, ?, ?)",
              (oferta_id, session["usuario_id"], fecha_postulacion))
    conn.commit()
    conn.close()

    return "<p>Postulación realizada con éxito.</p><p><a href='/ofertas'>Volver a ofertas</a></p>"
@app.route("/sobre-nosotros")
def sobre_nosotros():
    return render_template("sobre_nosotros.html")

@app.route("/servicios")
def servicios():
    return render_template("servicios.html")


@app.route("/recuperar-contrasena", methods=["GET", "POST"])
def recuperar_contrasena():
    if request.method == "POST":
        correo = request.form.get("correo")
        # Aquí puedes verificar si el correo existe en la base de datos y enviar un correo real o mostrar mensaje.
        return render_template("recuperar_confirmacion.html", correo=correo)
    return render_template("recuperar_contrasena.html")
@app.route("/contacto", methods=["GET", "POST"])
def contacto():
    if request.method == "POST":
        nombre = request.form["nombre"]
        email = request.form["email"]
        pais = request.form["pais"]
        ciudad = request.form["ciudad"]
        mensaje = request.form["mensaje"]
        # Aquí podrías guardar los datos o enviar un correo
        return render_template("contacto.html", mensaje_exito="¡Gracias por contactarnos!")

    return render_template("contacto.html")
@app.route("/editar_oferta/<int:oferta_id>", methods=["GET", "POST"])
def editar_oferta(oferta_id):
    # Verificar que el usuario esté logueado y sea empresa
    if "usuario_id" not in session or session.get("usuario_tipo") != "empresa":
        return redirect(url_for("login"))
    
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    
    # Obtener oferta y verificar que la oferta pertenezca a la empresa logueada
    c.execute("SELECT id, titulo, descripcion, empresa FROM ofertas WHERE id=?", (oferta_id,))
    oferta = c.fetchone()
    
    if not oferta:
        conn.close()
        return "<p>Oferta no encontrada.</p><p><a href='/panel'>Volver al panel</a></p>"
    
    if oferta[3] != session["usuario_nombre"]:
        conn.close()
        return "<p>No tienes permiso para editar esta oferta.</p><p><a href='/panel'>Volver al panel</a></p>"
    
    if request.method == "POST":
        nuevo_titulo = request.form["titulo"]
        nueva_descripcion = request.form["descripcion"]
        # Actualizar la oferta
        c.execute("UPDATE ofertas SET titulo=?, descripcion=? WHERE id=?", (nuevo_titulo, nueva_descripcion, oferta_id))
        conn.commit()
        conn.close()
        return redirect(url_for("panel"))
    
    conn.close()
    return render_template("editar_oferta.html", oferta=oferta)
@app.route("/eliminar_oferta/<int:oferta_id>", methods=["POST"])
def eliminar_oferta(oferta_id):
    if "usuario_id" not in session or session.get("usuario_tipo") != "empresa":
        return redirect(url_for("login"))

    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("SELECT empresa FROM ofertas WHERE id=?", (oferta_id,))
    oferta = c.fetchone()

    if not oferta:
        conn.close()
        return "<p>Oferta no encontrada.</p><p><a href='/panel'>Volver al panel</a></p>"

    if oferta[0] != session["usuario_nombre"]:
        conn.close()
        return "<p>No tienes permiso para eliminar esta oferta.</p><p><a href='/panel'>Volver al panel</a></p>"

    c.execute("DELETE FROM ofertas WHERE id=?", (oferta_id,))
    conn.commit()
    conn.close()

    return redirect(url_for("panel"))


# === Ruta principal para prueba ===
#@app.route("/")
#def home():
#    return '<h2>Bienvenido a la Bolsa de Empleo</h2><p><a href="/registro">Ir #a registro</a></p>'
@app.route("/")
def home():
    return render_template("index.html")

# === Ejecutar ===
if __name__ == "__main__":
    crear_base()
    app.run(debug=True)


