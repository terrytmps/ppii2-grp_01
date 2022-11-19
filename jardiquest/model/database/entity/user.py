from jardiquest.setup_sql import db

import re

regex = re.compile(r'([A-Za-z0-9]+[.-_])*[A-Za-z0-9]+@[A-Za-z0-9-]+(\.[A-Z|a-z]{2,})+')

class User(db.Model):
    __tablename__ = "user"

    email = db.Column(db.String(100), primary_key=True)
    password = db.Column(db.String(100), nullable=False)
    name = db.Column(db.String(1000), nullable=False)
    role = db.Column(db.String(15), default="Participant")
    balance = db.Column(db.Float(), default=0.00)
    recruitmentDate = db.Column(db.Date())

    idJardin = db.Column(db.String(10), db.ForeignKey("jardin.idJardin"))
    jardin = db.relationship("Jardin", back_populates="user")

    annonce = db.relationship("Annonce", back_populates="user")

    quete = db.relationship("Accepte", back_populates="user")

    def get_id(self):
        return self.email

    # return if the user as valid data or else the error message
    # use password not encoded because the sha256 algorithm will mess with the test of minimal len
    @staticmethod
    def is_valid_commit(email, name, password_not_encoded) -> (bool | str):
        if email is None:
            return "Veuillez utiliser une adresse mail"
        if not re.fullmatch(regex, email):
            return "Veuillez utiliser une adresse mail valide"
        if name == '' or name is None:
            return "Veuillez utiliser un nom"
        if password_not_encoded is None:
            return "Veuillez utiliser un mot de passe"
        if len(password_not_encoded) < 8:
            return "Veuillez utiliser un mot de passe avec au moins 8 caractères"
        return True


    @staticmethod
    def is_active():
        return False

    @staticmethod
    def is_authenticated():
        return True
