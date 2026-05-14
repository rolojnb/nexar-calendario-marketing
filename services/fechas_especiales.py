from __future__ import annotations

from datetime import date, datetime


FIXED_SPECIAL_DATES = {
    "01-01": {
        "nombre": "Ano Nuevo",
        "tipo": "fecha_especial",
        "prioridad": "alta",
        "sugerencia_titulo": "Empeza el ano con novedades",
        "sugerencia_texto": (
            "Arranca el ano con una comunicacion clara sobre promos, horarios "
            "y productos clave para tus clientes."
        ),
        "sugerencia_hashtags": "#AnoNuevo #NuevosComienzos #Promo",
    },
    "01-06": {
        "nombre": "Dia de Reyes",
        "tipo": "campana",
        "prioridad": "media",
        "sugerencia_titulo": "Ideas para Dia de Reyes",
        "sugerencia_texto": (
            "Mostra opciones de regalo, combos o destacados pensados para "
            "las compras de Dia de Reyes."
        ),
        "sugerencia_hashtags": "#DiaDeReyes #Regalos #Compras",
    },
    "02-14": {
        "nombre": "Dia de San Valentin",
        "tipo": "campana",
        "prioridad": "alta",
        "sugerencia_titulo": "Regalos para San Valentin",
        "sugerencia_texto": (
            "Invita a tus clientes a resolver sus compras con propuestas "
            "especiales para San Valentin."
        ),
        "sugerencia_hashtags": "#SanValentin #Regalos #Amor",
    },
    "05-01": {
        "nombre": "Dia del Trabajador",
        "tipo": "fecha_especial",
        "prioridad": "alta",
        "sugerencia_titulo": "Feliz Dia del Trabajador",
        "sugerencia_texto": (
            "Aprovecha para compartir un saludo cercano y recordar tus "
            "horarios especiales o beneficios del dia."
        ),
        "sugerencia_hashtags": "#DiaDelTrabajador #Comunidad #Tienda",
    },
    "12-25": {
        "nombre": "Navidad",
        "tipo": "temporada",
        "prioridad": "alta",
        "sugerencia_titulo": "Navidad en tu tienda",
        "sugerencia_texto": (
            "Comunica regalos, horarios especiales y propuestas pensadas "
            "para las compras navidenas."
        ),
        "sugerencia_hashtags": "#Navidad #Regalos #Fiestas",
    },
    "12-31": {
        "nombre": "Fin de ano",
        "tipo": "temporada",
        "prioridad": "alta",
        "sugerencia_titulo": "Cierre de ano con tu comunidad",
        "sugerencia_texto": (
            "Comparte un mensaje de cierre de ano, agradecimiento y mirada "
            "hacia lo que viene."
        ),
        "sugerencia_hashtags": "#FinDeAno #Gracias #Comunidad",
    },
}


YEARLY_SPECIAL_DATES = {
    2025: {
        "03-05": {
            "nombre": "Inicio de clases",
            "tipo": "temporada",
            "prioridad": "alta",
            "sugerencia_titulo": "Todo listo para la vuelta a clases",
            "sugerencia_texto": (
                "Organiza una campana con productos utiles para el regreso "
                "a clases y soluciones rapidas para las familias."
            ),
            "sugerencia_hashtags": "#VueltaAClases #InicioDeClases #Compras",
        },
        "10-19": {
            "nombre": "Dia de la Madre",
            "tipo": "campana",
            "prioridad": "alta",
            "sugerencia_titulo": "Regalos para mama",
            "sugerencia_texto": (
                "Presenta ideas de regalo y combos para el Dia de la Madre "
                "con una llamada clara a consultar stock."
            ),
            "sugerencia_hashtags": "#DiaDeLaMadre #Regalos #Familia",
        },
        "06-15": {
            "nombre": "Dia del Padre",
            "tipo": "campana",
            "prioridad": "alta",
            "sugerencia_titulo": "Ideas para regalar en el Dia del Padre",
            "sugerencia_texto": (
                "Destaca productos listos para regalar y comunica opciones "
                "de compra simples para el Dia del Padre."
            ),
            "sugerencia_hashtags": "#DiaDelPadre #Regalos #Promo",
        },
        "11-28": {
            "nombre": "Black Friday",
            "tipo": "campana",
            "prioridad": "alta",
            "sugerencia_titulo": "Black Friday en marcha",
            "sugerencia_texto": (
                "Anuncia descuentos, combos o beneficios de tiempo limitado "
                "para aprovechar el movimiento de Black Friday."
            ),
            "sugerencia_hashtags": "#BlackFriday #Ofertas #Descuentos",
        },
        "12-01": {
            "nombre": "Cyber Monday",
            "tipo": "campana",
            "prioridad": "alta",
            "sugerencia_titulo": "Cyber Monday con oportunidades",
            "sugerencia_texto": (
                "Comparte una propuesta digital clara con promociones "
                "puntuales para Cyber Monday."
            ),
            "sugerencia_hashtags": "#CyberMonday #Promos #ComprasOnline",
        },
    },
    2026: {
        "02-23": {
            "nombre": "Inicio de clases",
            "tipo": "temporada",
            "prioridad": "alta",
            "sugerencia_titulo": "Preparados para inicio de clases",
            "sugerencia_texto": (
                "Promueve productos utiles y recordatorios de compra para "
                "el regreso a clases con enfoque practico."
            ),
            "sugerencia_hashtags": "#InicioDeClases #VueltaAClases #Compras",
        },
        "10-18": {
            "nombre": "Dia de la Madre",
            "tipo": "campana",
            "prioridad": "alta",
            "sugerencia_titulo": "Regalos especiales para mama",
            "sugerencia_texto": (
                "Muestra propuestas listas para regalar y ayuda a resolver "
                "compras de ultimo momento para el Dia de la Madre."
            ),
            "sugerencia_hashtags": "#DiaDeLaMadre #Regalos #Tienda",
        },
        "06-21": {
            "nombre": "Dia del Padre",
            "tipo": "campana",
            "prioridad": "alta",
            "sugerencia_titulo": "Celebramos el Dia del Padre",
            "sugerencia_texto": (
                "Invita a descubrir productos recomendados para el Dia del Padre "
                "con foco en regalos utiles y faciles de elegir."
            ),
            "sugerencia_hashtags": "#DiaDelPadre #Regalos #Compras",
        },
        "11-27": {
            "nombre": "Black Friday",
            "tipo": "campana",
            "prioridad": "alta",
            "sugerencia_titulo": "Black Friday con promos fuertes",
            "sugerencia_texto": (
                "Lanza una comunicacion directa de descuentos, oportunidades "
                "por tiempo limitado y productos destacados."
            ),
            "sugerencia_hashtags": "#BlackFriday #Promo #Descuentos",
        },
        "11-30": {
            "nombre": "Cyber Monday",
            "tipo": "campana",
            "prioridad": "alta",
            "sugerencia_titulo": "Cyber Monday para vender mas",
            "sugerencia_texto": (
                "Presenta ofertas concretas y una llamada a la accion orientada "
                "a compras rapidas durante Cyber Monday."
            ),
            "sugerencia_hashtags": "#CyberMonday #Promos #Ventas",
        },
    },
    2027: {
        "03-01": {
            "nombre": "Inicio de clases",
            "tipo": "temporada",
            "prioridad": "alta",
            "sugerencia_titulo": "Todo para el inicio de clases",
            "sugerencia_texto": (
                "Organiza un mensaje con productos, recordatorios y beneficios "
                "para el regreso a clases."
            ),
            "sugerencia_hashtags": "#InicioDeClases #VueltaAClases #Temporada",
        },
        "10-17": {
            "nombre": "Dia de la Madre",
            "tipo": "campana",
            "prioridad": "alta",
            "sugerencia_titulo": "Ideas de regalo para el Dia de la Madre",
            "sugerencia_texto": (
                "Comparte sugerencias concretas y mensajes emocionales "
                "para impulsar compras de regalo."
            ),
            "sugerencia_hashtags": "#DiaDeLaMadre #Regalos #Campana",
        },
        "06-20": {
            "nombre": "Dia del Padre",
            "tipo": "campana",
            "prioridad": "alta",
            "sugerencia_titulo": "Dia del Padre con propuestas utiles",
            "sugerencia_texto": (
                "Destaca opciones de compra simples y productos pensados "
                "para sorprender en el Dia del Padre."
            ),
            "sugerencia_hashtags": "#DiaDelPadre #Regalos #Negocio",
        },
        "11-26": {
            "nombre": "Black Friday",
            "tipo": "campana",
            "prioridad": "alta",
            "sugerencia_titulo": "Black Friday: tus mejores oportunidades",
            "sugerencia_texto": (
                "Usa mensajes urgentes y concretos para reforzar el atractivo "
                "de tus ofertas de Black Friday."
            ),
            "sugerencia_hashtags": "#BlackFriday #Ofertas #Campana",
        },
        "11-29": {
            "nombre": "Cyber Monday",
            "tipo": "campana",
            "prioridad": "alta",
            "sugerencia_titulo": "Cyber Monday para mover ventas",
            "sugerencia_texto": (
                "Aprovecha el dia para comunicar combos, promociones y una "
                "propuesta pensada para compras rapidas."
            ),
            "sugerencia_hashtags": "#CyberMonday #Ventas #Promo",
        },
    },
}


def _normalize_date(value: date | datetime | str) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return datetime.fromisoformat(value).date()


def obtener_fecha_especial(fecha: date | datetime | str) -> dict | None:
    normalized_date = _normalize_date(fecha)
    month_day = normalized_date.strftime("%m-%d")

    special_data = FIXED_SPECIAL_DATES.get(month_day)
    if not special_data:
        special_data = YEARLY_SPECIAL_DATES.get(normalized_date.year, {}).get(month_day)

    if not special_data:
        return None

    return {
        **special_data,
        "fecha": normalized_date.isoformat(),
    }
