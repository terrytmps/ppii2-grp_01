from flask import redirect, url_for, render_template, abort, flash
from flask_login import current_user
from jardiquest.setup_sql import db
from sqlalchemy.sql import func
import uuid
import math
from datetime import datetime
from jardiquest.model.database.entity.catalogue import Catalogue
from jardiquest.model.database.entity.recolte import Recolte
from jardiquest.model.database.entity.commande import Commande
from jardiquest.model.database.entity.user import User



def display_sell_catalogue():
    if current_user.role != "Proprietaire":
        abort(403)

    catalogue = db.session.query(Catalogue.name, Catalogue.imagePath, Catalogue.type, func.round((func.sum(Recolte.cost * Recolte.quantity)/func.sum(Recolte.quantity)),2).label("mean_cost"), func.min(Recolte.cost).label("min_cost"), func.sum(Recolte.quantity).label("quantity")).join(Recolte, isouter=True).group_by(Catalogue.name).all()
    return render_template('sell_catalogue.html', catalogue = catalogue, garden = current_user.jardin)



def display_sell_product(product):
    if current_user.role != "Proprietaire":
        abort(403)

    # TODO formulaire pour la quantité et le prix    
    product = db.session.query(Catalogue.idCatalogue, Catalogue.name, Catalogue.imagePath, Catalogue.description, Catalogue.description_source).filter(Catalogue.name == product).first()
    infos = db.session.query(func.min(Recolte.cost).label("min_cost")).filter(Recolte.idCatalogue == product.idCatalogue, Recolte.idJardin == current_user.jardin.idJardin).group_by(Recolte.idCatalogue).first()
    sellings = db.session.query(Recolte.idRecolte, Recolte.quantity, Recolte.cost, Recolte.date).filter(Recolte.idCatalogue == product.idCatalogue, Recolte.idJardin == current_user.jardin.idJardin).all()
    return render_template('sell_product.html', product = product, infos=infos, sellings = sellings, garden = current_user.jardin)


def sell_product(product, quantity, cost):
    idCatalogue = db.session.query(Catalogue.idCatalogue).filter(Catalogue.name == product).first().idCatalogue
    if current_user.role != "Proprietaire" or not idCatalogue or quantity <= 0 or cost < 0:
        abort(403)
    
    recolte = Recolte(idRecolte = uuid.uuid1().hex, idCatalogue = idCatalogue, idJardin = current_user.jardin.idJardin, quantity = quantity, cost = cost, date = datetime.now())
    db.session.add(recolte)
    db.session.commit()
    return redirect(url_for('controller.sell_catalogue'))


def cancel_selling(selling_id):
    recolte = db.session.query(Recolte).filter(Recolte.idRecolte == selling_id).first()
    if recolte is None or current_user.role != "Proprietaire" or recolte.idJardin != current_user.jardin.idJardin:
        abort(403)
    db.session.delete(recolte)
    db.session.commit()
    product_name = db.session.query(Catalogue.name).filter(Catalogue.idCatalogue == recolte.idCatalogue).first().name
    return redirect(url_for('controller.sell_product', product = product_name))


def display_market():
    garden = current_user.jardin
    if garden is None:
        flash("Vous devez d'abord créer ou rejoindre un jardin pour accéder à cette page", 'error')
        return redirect(url_for('controller.garden'))

    produits = db.session.query(func.min(Recolte.cost).label("cheaper_price"), func.sum(Recolte.quantity).label("quantity"), Catalogue.name, Catalogue.type, Catalogue.imagePath).join(Catalogue).group_by(Catalogue.name).filter(Recolte.idJardin == garden.idJardin).having(func.sum(Recolte.quantity) >= 0.1).all()
    return render_template('market.html', produits=produits, garden=garden)



def display_market_product(product):
    garden = current_user.jardin
    if garden is None:
        flash("Vous devez d'abord créer ou rejoindre un jardin pour accéder à cette page", 'error')
        return redirect(url_for('controller.garden'))

    product_infos = db.session.query(Catalogue).filter(Catalogue.name == product).first()
    if product_infos is None:
        abort(404)
    selling_products = db.session.query(Recolte).filter(Recolte.idJardin == garden.idJardin, Recolte.idCatalogue == product_infos.idCatalogue, Recolte.quantity >= 0.1).order_by(Recolte.cost).all()
    return render_template('market_product.html', product=product_infos, sellings=selling_products, garden=garden, user=current_user)


def market_buy(quantity, selling_id):
    selling = db.session.query(Recolte).filter(Recolte.idRecolte == selling_id).first()
    if selling is None or quantity > selling.quantity or quantity <= 0 or selling.jardin != current_user.jardin:
        abort(404)

    totalPrice = selling.cost * quantity

    if current_user.balance < totalPrice:
        flash("Votre solde n'est pas suffisant", "error")
    else:
        # If no error : 
        # Decrease quantity, and delete if no more
        selling.quantity -= quantity
        selling.quantity = math.floor(selling.quantity*100)/100
    
        # Decrease user balance
        current_user.balance -= totalPrice
        current_user.balance = math.floor(current_user.balance*100)/100

        # Create an order
        commande = Commande(idCommande = uuid.uuid1().hex, acheteur=current_user.email, idRecolte=selling_id, quantite=quantity, cout = totalPrice , dateAchat = datetime.now())
        db.session.add(commande)
        db.session.commit()

    return redirect(url_for('controller.market_product', product=selling.catalogue.name))



def display_orders():
    garden = current_user.jardin
    if garden is None:
        flash("Vous devez d'abord créer ou rejoindre un jardin pour accéder à cette page", "error")
        return redirect(url_for('controller.garden'))

    if current_user.role != "Proprietaire":
        abort(403)
    orders = db.session.query(Commande.idCommande, Commande.quantite, Commande.acheteur.label("email"), User.name.label("username"), Commande.dateAchat, Commande.cout, Catalogue.name.label("productName")).join(Recolte.commande).join(Catalogue).join(User).filter(Recolte.idJardin == garden.idJardin, Commande.traitee == False).order_by(Commande.dateAchat).all()
    return render_template('orders.html', orders=orders, garden=garden)


def confirm_order(order_id):
    garden = current_user.jardin
    if garden is None:
        flash("Vous devez d'abord créer ou rejoindre un jardin pour accéder à cette page", "error")
        return redirect(url_for('controller.garden'))

    if current_user.role != "Proprietaire":
        abort(403)

    order = db.session.query(Commande).filter(Commande.idCommande == order_id).first()
    
    if order is None:
        abort(404)
    
    order.traitee = True
    db.session.commit()
    return redirect(url_for('controller.display_orders'))