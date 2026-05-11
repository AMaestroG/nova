#!/usr/bin/env python3
"""
Inicializa la base de datos del Sistema Centinela
Nova Homonexus - MAYORDOMO

Crea todas las tablas en PostgreSQL y ejecuta el schema.sql.

USO:
    python init_db.py
"""

import sys
import logging
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy_utils import database_exists, create_database

from centinela.config import DB_URL, DB_CONFIG

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
)
logger = logging.getLogger("centinela.init_db")


def init_database():
    """Inicializa la base de datos Centinela."""
    logger.info("=" * 60)
    logger.info("INICIALIZANDO BASE DE DATOS CENTINELA")
    logger.info("Host: %s:%s", DB_CONFIG["host"], DB_CONFIG["port"])
    logger.info("Base de datos: %s", DB_CONFIG["database"])
    logger.info("=" * 60)

    # Crear engine
    engine = create_engine(DB_URL)

    # Crear base de datos si no existe
    if not database_exists(engine.url):
        logger.info("Creando base de datos: %s", DB_CONFIG["database"])
        create_database(engine.url)
        logger.info("Base de datos creada exitosamente")
    else:
        logger.info("Base de datos ya existe")

    # Ejecutar schema.sql
    schema_path = Path(__file__).parent / "db" / "schema.sql"
    if schema_path.exists():
        logger.info("Ejecutando schema.sql...")
        with open(schema_path, "r") as f:
            schema_sql = f.read()

        with engine.connect() as conn:
            # Ejecutar cada statement por separado
            statements = schema_sql.split(";")
            for i, stmt in enumerate(statements):
                stmt = stmt.strip()
                if stmt and not stmt.startswith("--"):
                    try:
                        conn.execute(text(stmt))
                        if i % 10 == 0:
                            logger.debug(
                                "Statement %d ejecutado", i
                            )
                    except Exception as e:
                        logger.warning(
                            "Statement %d: %s", i, str(e)[:100]
                        )
            conn.commit()

        logger.info("Schema.sql ejecutado exitosamente")
    else:
        logger.warning(
            "schema.sql no encontrado en %s", schema_path
        )

    # Crear tablas vía SQLAlchemy models
    logger.info("Creando tablas via SQLAlchemy...")
    from centinela.db.models import Base
    Base.metadata.create_all(engine)

    # Verificar tablas creadas
    with engine.connect() as conn:
        result = conn.execute(
            text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name LIKE 'centinela_%'
                ORDER BY table_name
            """)
        )
        tablas = [row[0] for row in result]

    logger.info("Tablas creadas verificadas:")
    for tabla in tablas:
        logger.info("  ✓ %s", tabla)

    logger.info("=" * 60)
    logger.info("BASE DE DATOS INICIALIZADA EXITOSAMENTE")
    logger.info("Tablas creadas: %d", len(tablas))
    logger.info("=" * 60)

    return tablas


if __name__ == "__main__":
    tablas = init_database()
    sys.exit(0)
