"""Database management service."""
from __future__ import annotations

import logging
import secrets
import string
from typing import Any, Dict, List, Literal, Optional

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.db_credential import DBCredential
from app.schemas.database import DatabaseCreate, DatabaseResponse, DatabaseUserCreate
from app.services.encryption_service import get_encryption_service

logger = logging.getLogger(__name__)
settings = get_settings()


class DatabaseService:
    """Service for managing MariaDB databases.

    Handles database and user creation, deletion, privilege management,
    and query execution for both Blog and Mailserver systems.
    """

    def __init__(self, db: Session):
        """Initialize database service.

        Args:
            db: Unified portal database session
        """
        self.db = db
        self.encryption = get_encryption_service()
        self._engines: Dict[str, Engine] = {}

    def _get_engine(self, target: Literal["blog", "mailserver"]) -> Engine:
        """Get database engine for target system.

        Args:
            target: Target system (blog or mailserver)

        Returns:
            SQLAlchemy engine
        """
        if target not in self._engines:
            if target == "blog":
                url = settings.blog_database_url
            elif target == "mailserver":
                url = settings.mailserver_database_url
            else:
                raise ValueError(f"Invalid target system: {target}")

            self._engines[target] = create_engine(url, pool_pre_ping=True)

        return self._engines[target]

    def list_databases(self, target: Literal["blog", "mailserver"]) -> List[DatabaseResponse]:
        """List all databases in target system.

        Args:
            target: Target system

        Returns:
            List of databases with size and table count
        """
        engine = self._get_engine(target)

        try:
            with engine.connect() as conn:
                # Query databases with size information
                query = text("""
                    SELECT
                        SCHEMA_NAME as database_name,
                        DEFAULT_CHARACTER_SET_NAME as charset,
                        DEFAULT_COLLATION_NAME as collation,
                        ROUND(SUM(DATA_LENGTH + INDEX_LENGTH) / 1024 / 1024, 2) as size_mb,
                        COUNT(TABLE_NAME) as table_count
                    FROM information_schema.SCHEMATA
                    LEFT JOIN information_schema.TABLES
                        ON SCHEMA_NAME = TABLE_SCHEMA
                    WHERE SCHEMA_NAME NOT IN ('information_schema', 'mysql', 'performance_schema', 'sys')
                    GROUP BY SCHEMA_NAME
                    ORDER BY SCHEMA_NAME
                """)

                result = conn.execute(query)
                databases = []

                for row in result:
                    databases.append(
                        DatabaseResponse(
                            database_name=row.database_name,
                            charset=row.charset or "utf8mb4",
                            collation=row.collation or "utf8mb4_unicode_ci",
                            size_mb=float(row.size_mb or 0),
                            table_count=int(row.table_count or 0),
                        )
                    )

                return databases

        except SQLAlchemyError as e:
            logger.error(f"Failed to list databases for {target}: {e}")
            raise ValueError(f"Failed to list databases: {e}")

    def create_database(
        self,
        db_create: DatabaseCreate,
    ) -> DatabaseResponse:
        """Create a new database.

        Args:
            db_create: Database creation data

        Returns:
            Created database info

        Raises:
            ValueError: If creation fails
        """
        engine = self._get_engine(db_create.target_system)

        try:
            with engine.connect() as conn:
                # Create database
                conn.execute(
                    text(
                        f"CREATE DATABASE `{db_create.database_name}` "
                        f"CHARACTER SET {db_create.charset} "
                        f"COLLATE {db_create.collation}"
                    )
                )
                conn.commit()

                # Create dedicated user if requested
                if db_create.create_user:
                    username = db_create.username or db_create.database_name
                    password = db_create.password or self._generate_password()

                    # Create user
                    conn.execute(text(f"CREATE USER '{username}'@'%' IDENTIFIED BY '{password}'"))

                    # Grant all privileges on database
                    conn.execute(text(f"GRANT ALL PRIVILEGES ON `{db_create.database_name}`.* TO '{username}'@'%'"))
                    conn.execute(text("FLUSH PRIVILEGES"))
                    conn.commit()

                    # Store encrypted credentials
                    credential = DBCredential(
                        database_name=db_create.database_name,
                        username=username,
                        password_encrypted=self.encryption.encrypt(password),
                        host=settings.blog_db_host if db_create.target_system == "blog" else settings.mailserver_db_host,
                        port=settings.blog_db_port if db_create.target_system == "blog" else settings.mailserver_db_port,
                        target_system=db_create.target_system,
                    )

                    self.db.add(credential)
                    self.db.commit()

                logger.info(f"Database created: {db_create.database_name} ({db_create.target_system})")

                return DatabaseResponse(
                    database_name=db_create.database_name,
                    charset=db_create.charset,
                    collation=db_create.collation,
                    size_mb=0.0,
                    table_count=0,
                )

        except SQLAlchemyError as e:
            logger.error(f"Failed to create database: {e}")
            raise ValueError(f"Failed to create database: {e}")

    def delete_database(self, database_name: str, target: Literal["blog", "mailserver"]) -> None:
        """Delete a database.

        Args:
            database_name: Database name
            target: Target system

        Raises:
            ValueError: If deletion fails
        """
        engine = self._get_engine(target)

        try:
            with engine.connect() as conn:
                # Drop database
                conn.execute(text(f"DROP DATABASE IF EXISTS `{database_name}`"))
                conn.commit()

                # Delete stored credentials
                credential = self.db.query(DBCredential).filter(
                    DBCredential.database_name == database_name,
                    DBCredential.target_system == target,
                ).first()

                if credential:
                    # Drop user before deleting credential
                    try:
                        conn.execute(text(f"DROP USER IF EXISTS '{credential.username}'@'%'"))
                        conn.commit()
                    except SQLAlchemyError as e:
                        logger.warning(f"Failed to drop user {credential.username}: {e}")

                    self.db.delete(credential)
                    self.db.commit()

                logger.info(f"Database deleted: {database_name} ({target})")

        except SQLAlchemyError as e:
            logger.error(f"Failed to delete database: {e}")
            raise ValueError(f"Failed to delete database: {e}")

    def list_users(self, target: Literal["blog", "mailserver"]) -> List[Dict[str, Any]]:
        """List database users.

        Args:
            target: Target system

        Returns:
            List of database users
        """
        engine = self._get_engine(target)

        try:
            with engine.connect() as conn:
                result = conn.execute(text("SELECT User, Host FROM mysql.user WHERE User != 'root' ORDER BY User"))

                users = []
                for row in result:
                    users.append({"username": row.User, "host": row.Host})

                return users

        except SQLAlchemyError as e:
            logger.error(f"Failed to list users: {e}")
            raise ValueError(f"Failed to list users: {e}")

    def create_user(self, user_create: DatabaseUserCreate) -> Dict[str, str]:
        """Create a database user.

        Args:
            user_create: User creation data

        Returns:
            Created user info

        Raises:
            ValueError: If creation fails
        """
        engine = self._get_engine(user_create.target_system)

        try:
            with engine.connect() as conn:
                # Create user
                conn.execute(
                    text(
                        f"CREATE USER '{user_create.username}'@'{user_create.host}' "
                        f"IDENTIFIED BY '{user_create.password}'"
                    )
                )
                conn.commit()

                logger.info(f"User created: {user_create.username}@{user_create.host}")

                return {
                    "username": user_create.username,
                    "host": user_create.host,
                }

        except SQLAlchemyError as e:
            logger.error(f"Failed to create user: {e}")
            raise ValueError(f"Failed to create user: {e}")

    def execute_query(
        self,
        query_str: str,
        target: Literal["blog", "mailserver"],
        database_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute SQL query.

        Args:
            query_str: SQL query string
            target: Target system
            database_name: Database to use (optional)

        Returns:
            Query results

        Raises:
            ValueError: If query execution fails
        """
        engine = self._get_engine(target)

        try:
            with engine.connect() as conn:
                # Use specific database if provided
                if database_name:
                    conn.execute(text(f"USE `{database_name}`"))

                # Execute query
                result = conn.execute(text(query_str))
                conn.commit()

                # Return results based on query type
                if result.returns_rows:
                    rows = [dict(row._mapping) for row in result]
                    return {"success": True, "rows_affected": len(rows), "results": rows}
                else:
                    return {"success": True, "rows_affected": result.rowcount}

        except SQLAlchemyError as e:
            logger.error(f"Query execution failed: {e}")
            return {"success": False, "error": str(e)}

    @staticmethod
    def _generate_password(length: int = 16) -> str:
        """Generate a random password.

        Args:
            length: Password length

        Returns:
            Random password
        """
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        return "".join(secrets.choice(alphabet) for _ in range(length))


def get_database_service(db: Session) -> DatabaseService:
    """Get database service instance.

    Args:
        db: Database session

    Returns:
        DatabaseService instance
    """
    return DatabaseService(db)
