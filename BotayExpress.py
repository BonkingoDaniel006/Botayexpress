import random
from flask import Flask,jsonify, render_template, request, redirect, url_for, session
from werkzeug.utils import secure_filename
import os

app = Flask(__name__)
app.secret_key = "super_secret_key"


#connexion à la bas de données

import mysql.connector

conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="Daniel12349",
    database="botayexpress"
)

cursor = conn.cursor(dictionary=True)




@app.route("/")
def home():
    return render_template("connexion.html")


@app.route("/users")
def get_users():
    cursor.execute("SELECT * FROM buyers")
    users = cursor.fetchall()
    return jsonify(users)


@app.route("/create_account")
def create_account():
    return render_template("creation_compte_acheteur.html")

@app.route("/account_setup", methods=["POST"])
def account_setup():
    last_name = request.form["last_name"]
    first_name = request.form["first_name"]
    middle_name = request.form["middle_name"]
    email = request.form["email"]
    naissance = request.form["naissance"]
    adresse = request.form["adresse"]
    nom_boutique = request.form["nom_boutique"]
    description = request.form["description"]
    password = request.form["password"]
    confirm_password = request.form["confirm_password"]

    if password != confirm_password:
        return render_template("creation_compte_acheteur.html",
                               error="Les mots de passe ne correspondent pas.")

    cursor.execute("""
        INSERT INTO buyers (last_name, first_name, middle_name, email, naissance, adresse, nom_boutique, description, password)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (last_name, first_name, middle_name, email, naissance, adresse, nom_boutique, description, password))

    conn.commit()
    print("insert ok")

    return redirect(url_for("home"))



@app.route("/fil_actu", methods=["GET", "POST"])
def fil_actu():
    if request.method == "GET":
        if "user" in session:
            user = session["user"]

            # Récupération produits + nom boutique
            cursor.execute("""
                SELECT p.*, b.nom_boutique
                FROM products p
                JOIN buyers b ON p.seller_id = b.id
            """)
            produits = cursor.fetchall()

            # Mélanger
            random.shuffle(produits)

            return render_template("fil_actu.html",
                                   name=user["first_name"],
                                   produits=produits,
                                   user=user)
        else:
            return redirect(url_for("connexion"))

    # ----- PARTIE POST (connexion) -----

    email = request.form.get("email")
    motdepasse = request.form.get("motdepasse")

    cursor.execute("SELECT * FROM buyers")
    users = cursor.fetchall()

    for user in users:
        if user["email"] == email and user["password"] == motdepasse:
            session["user"] = user

            # IMPORTANT : même requête JOIN ici !
            cursor.execute("""
                SELECT p.*, b.nom_boutique
                FROM products p
                JOIN buyers b ON p.seller_id = b.id
            """)
            produits = cursor.fetchall()
            random.shuffle(produits)

            return render_template("fil_actu.html",
                                   name=user["first_name"],
                                   produits=produits,
                                   user=user)

    return render_template("connexion.html",
                           error="Identifiants incorrects. Veuillez réessayer.")
@app.route("/produit/<int:product_id>")
def produit_details(product_id):
    user = session.get("user")

    cursor.execute("""
        SELECT p.*, b.nom_boutique
        FROM products p
        JOIN buyers b ON p.seller_id = b.id
        WHERE p.id = %s
    """, (product_id,))
    
    produit = cursor.fetchone()

    if produit:
        return render_template("detail_produit.html", produit=produit, user=user)

    return "Produit introuvable", 404

@app.route("/add_product/<int:product_id>", methods=["GET", "POST"])
def add_product(product_id):
    user = session.get("user")

    cursor.execute("""
        SELECT p.*, b.nom_boutique
        FROM products p
        JOIN buyers b ON p.seller_id = b.id
        WHERE p.id = %s
    """, (product_id,))
    
    produit = cursor.fetchone()

    if produit:
        return render_template(
            "detail_produit.html",
            produit=produit,
            panier="Produit ajouté au panier !",
            user=user
        )

    return "Produit introuvable", 404

@app.route("/profil_acheteur")
def profil_acheteur():
    user = session.get("user")

    if not user:
        return redirect(url_for("home"))

    return render_template("profil_acheteur.html", user=user)
@app.route("/paiement")
def paiement():
    user = session.get("user")

    if not user:
        return redirect(url_for("home"))

    return render_template("paiement.html", user=user)
@app.route("/avis_commande")
def avis_commande():
    return render_template("avis_commande.html")


@app.route("/profil_vendeur")
def profil_vendeur():
    user = session.get("user")

    if not user:
        return redirect(url_for("home"))

    cursor.execute("SELECT * FROM products WHERE seller_id = %s", (user["id"],))
    produits_vendeur = cursor.fetchall()

    return render_template("profil_vendeur.html", user=user, produits=produits_vendeur)

@app.route("/modifier_profil_acheteur")
def modifier_profil_acheteur():
    user = session.get("user")

    if not user:
        return redirect(url_for("home"))

    return render_template("modifier_profil.html", user=user)



@app.route("/modifier_profil", methods=["GET", "POST"])
def modifier_profil():

    user = session.get("user")
    if not user:
        return redirect(url_for("home"))

    user_id = user["id"]

    # Récupérer l'utilisateur actuel
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM buyers WHERE id=%s", (user_id,))
    user = cursor.fetchone()

    if request.method == "POST":

        # Champs texte
        email = request.form["email"]
        first_name = request.form["first_name"]
        last_name = request.form["last_name"]
        middle_name = request.form.get("middle_name")
        adresse = request.form["adresse"]
        naissance = request.form["naissance"]
        nom_boutique = request.form.get("nom_boutique")
        description = request.form.get("description")
        motdepasse = request.form.get("motdepasse")
        confirmer = request.form.get("confirmer")

        # Gestion de la photo
        file = request.files.get("profil")
        profil_path = user["profil"]  # valeur par défaut

        if file and file.filename != "":
            filename = secure_filename(file.filename)
            profil_path = os.path.join("static/profils", filename)
            file.save(profil_path)

        # Mise à jour SQL
        if motdepasse and motdepasse == confirmer:
            cursor.execute("""
                UPDATE buyers SET email=%s, first_name=%s, last_name=%s,
                middle_name=%s, adresse=%s, naissance=%s, password=%s,
                profil=%s, nom_boutique=%s, description=%s WHERE id=%s
            """, (email, first_name, last_name, middle_name, adresse, naissance,
                  motdepasse, profil_path, nom_boutique, description, user_id))
        else:
            cursor.execute("""
                UPDATE buyers SET email=%s, first_name=%s, last_name=%s,
                middle_name=%s, adresse=%s, naissance=%s, profil=%s, nom_boutique=%s, description=%s
                WHERE id=%s
            """, (email, first_name, last_name, middle_name, adresse, naissance,
                  profil_path, nom_boutique, description, user_id))

        conn.commit()
        return redirect("/profil_acheteur")

    # Si GET → afficher la page
    return render_template("modifier_profil.html", user=user)

@app.route("/ajouter_produit")
def ajouter_produit():
    user = session.get("user")

    if not user:
        return redirect(url_for("home"))

    return render_template("ajouter_produit.html", user=user)

@app.route("/enregistrer_produit", methods=["POST"])
def enregistrer_produit():
    user = session.get("user")

    if not user:
        return redirect(url_for("home"))

    # Récupération des champs texte
    nom_produit = request.form.get("nom_produit")
    prix = request.form.get("prix")
    description = request.form.get("description")

    # Récupération du fichier image
    image_file = request.files.get("image_url")

    # Gestion de l'image uploadée
    if image_file and image_file.filename != "":
        filename = secure_filename(image_file.filename)
        image_path = os.path.join("static/uploads", filename)

        image_file.save(image_path)
        image_url = "/" + image_path.replace("\\", "/")

    else:
        image_url = None  # ou une image par défaut

    # Insertion dans la base
    cursor.execute("""
        INSERT INTO products (seller_id, name, price, description, image_url)
        VALUES (%s, %s, %s, %s, %s)
    """, (user["id"], nom_produit, prix, description, image_url))

    conn.commit()
    print("Produit ajouté avec succès")

    return redirect(url_for("profil_vendeur"))
@app.route("/detail_produits_vendeur")
def detail_produits_vendeur():
    user = session.get("user")

    if not user:
        return redirect(url_for("home"))

    cursor.execute("SELECT * FROM products WHERE seller_id = %s", (user["id"],))
    produits_vendeur = cursor.fetchall()

    return render_template("detail_produits_vendeur.html", user=user, produits=produits_vendeur)

@app.route("/acceuil")
def acceuil():
        return redirect(url_for("fil_actu"))


if __name__ == "__main__":
    app.run(debug=True)
