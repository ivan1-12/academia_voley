from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required
import graphene
from models import get_db


class JugadorType(graphene.ObjectType):
    id = graphene.Int()
    nombre = graphene.String()
    apellido = graphene.String()
    email = graphene.String()
    genero = graphene.String()
    edad = graphene.Int()


class Query(graphene.ObjectType):
    jugadores = graphene.List(
        JugadorType,
        min_age=graphene.Int(),
        max_age=graphene.Int(),
        genero=graphene.String(),
        search=graphene.String(),
    )

    def resolve_jugadores(self, info, min_age=None, max_age=None, genero=None, search=None):
        db = get_db()
        cur = db.cursor()
        try:
            query_parts = ["SELECT id, nombre, apellido, email, genero, edad FROM usuarios WHERE rol = 'jugador'"]
            params = []

            if min_age is not None:
                query_parts.append("AND edad >= %s")
                params.append(min_age)
            if max_age is not None:
                query_parts.append("AND edad <= %s")
                params.append(max_age)
            if genero:
                query_parts.append("AND LOWER(genero) = LOWER(%s)")
                params.append(genero)
            if search:
                search_term = f"%{search}%"
                query_parts.append(
                    "AND (nombre LIKE %s OR apellido LIKE %s OR email LIKE %s)"
                )
                params.extend([search_term, search_term, search_term])

            query_parts.append("ORDER BY nombre, apellido")
            cur.execute(" ".join(query_parts), tuple(params))
            rows = cur.fetchall()
            return [JugadorType(**row) for row in rows]
        except Exception as e:
            current_app.logger.exception("Error resolviendo GraphQL jugadores: %s", e)
            return []
        finally:
            cur.close()


graphql_bp = Blueprint("graphql_api", __name__)
schema = graphene.Schema(query=Query)


@graphql_bp.route("/graphql", methods=["GET", "POST"])
@login_required
def graphql_endpoint():
    if request.method == "GET":
        return jsonify(
            {
                "message": "Usa POST con un body JSON que contenga 'query' y opcionalmente 'variables'.",
                "example": {
                    "query": "{ jugadores(minAge: 14, genero: \"Femenino\") { id nombre apellido email genero edad } }"
                },
            }
        )

    payload = request.get_json(silent=True)
    if not payload or "query" not in payload:
        return jsonify({"errors": ["Payload inválido: se requiere 'query'."]}), 400

    result = schema.execute(
        payload.get("query"),
        variable_values=payload.get("variables"),
        context_value={"user": request.remote_user},
    )

    response = {}
    if result.errors:
        response["errors"] = [str(error) for error in result.errors]
    if result.data is not None:
        response["data"] = result.data

    status_code = 400 if result.errors else 200
    return jsonify(response), status_code
