"""Database models and configuration."""

import logging
import os
from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    create_engine,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, relationship, sessionmaker

Base = declarative_base()
logger = logging.getLogger(__name__)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False, index=True)
    username = Column(String(255))
    first_name = Column(String(255))
    last_name = Column(String(255))
    language_code = Column(String(10), default="es")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)

    subscriptions = relationship("Subscription", back_populates="user", cascade="all, delete-orphan")
    bookmarks = relationship("Bookmark", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<User(telegram_id={self.telegram_id}, username={self.username})>"


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    subscription_type = Column(String(20), nullable=False)  # 'theme' or 'dataset'
    subscription_id = Column(String(255), nullable=False)  # theme name or dataset_id
    subscription_name = Column(String(500))  # human-readable name
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)

    user = relationship("User", back_populates="subscriptions")

    __table_args__ = (
        UniqueConstraint("user_id", "subscription_type", "subscription_id", name="unique_user_subscription"),
    )

    def __repr__(self) -> str:
        return f"<Subscription(user_id={self.user_id}, type={self.subscription_type}, id={self.subscription_id})>"


class DatasetSnapshot(Base):
    __tablename__ = "dataset_snapshots"

    id = Column(Integer, primary_key=True)
    dataset_id = Column(String(255), nullable=False, index=True)
    modified = Column(String(50))
    data_processed = Column(String(50))
    metadata_processed = Column(String(50))
    records_count = Column(Integer, default=0)
    themes = Column(Text)  # JSON serialized list
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<DatasetSnapshot(dataset_id={self.dataset_id}, modified={self.modified})>"


class ThemeSnapshot(Base):
    __tablename__ = "theme_snapshots"

    id = Column(Integer, primary_key=True)
    theme_name = Column(String(255), nullable=False, index=True)
    dataset_ids = Column(Text)  # JSON serialized list of dataset IDs
    dataset_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<ThemeSnapshot(theme={self.theme_name}, count={self.dataset_count})>"


class Bookmark(Base):
    __tablename__ = "bookmarks"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    dataset_id = Column(String(255), nullable=False)
    dataset_title = Column(String(500))
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="bookmarks")

    __table_args__ = (UniqueConstraint('user_id', 'dataset_id', name='unique_user_bookmark'),)

    def __repr__(self) -> str:
        return f"<Bookmark(user_id={self.user_id}, dataset_id={self.dataset_id})>"


class DatabaseManager:
    def __init__(self, database_url: Optional[str] = None):
        self.database_url = database_url or os.getenv("DATABASE_URL", "sqlite:///jcyl_bot.db")
        self.engine = create_engine(self.database_url, echo=False)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

    def create_tables(self) -> None:
        """Create all tables."""
        Base.metadata.create_all(bind=self.engine)

    def get_session(self) -> Session:
        """Get database session."""
        return self.SessionLocal()

    def get_or_create_user(self, telegram_id: int, **kwargs) -> int:
        """Get or create user by telegram ID. Returns user.id."""
        session = self.get_session()
        try:
            user = session.query(User).filter(User.telegram_id == telegram_id).first()
            if not user:
                user = User(telegram_id=telegram_id, **kwargs)
                session.add(user)
                session.commit()
                session.refresh(user)
            else:
                # Update user info if provided
                for key, value in kwargs.items():
                    if hasattr(user, key) and value is not None:
                        setattr(user, key, value)
                user.updated_at = datetime.utcnow()
                session.commit()
            return user.id  # Return only the ID to avoid session issues
        finally:
            session.close()

    def add_subscription(
        self, 
        user_id: int, 
        subscription_type: str, 
        subscription_id: str, 
        subscription_name: Optional[str] = None
    ) -> bool:
        """Add subscription for user. Returns True if added, False if already exists."""
        session = self.get_session()
        try:
            existing = session.query(Subscription).filter(
                Subscription.user_id == user_id,
                Subscription.subscription_type == subscription_type,
                Subscription.subscription_id == subscription_id
            ).first()
            
            if existing:
                if not existing.is_active:
                    existing.is_active = True
                    session.commit()
                return False
                
            subscription = Subscription(
                user_id=user_id,
                subscription_type=subscription_type,
                subscription_id=subscription_id,
                subscription_name=subscription_name or subscription_id
            )
            session.add(subscription)
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"Error adding subscription: {e}", exc_info=True)
            raise
        finally:
            session.close()

    def remove_subscription(self, user_id: int, subscription_id: int) -> bool:
        """Remove subscription by ID. Returns True if removed."""
        session = self.get_session()
        try:
            subscription = session.query(Subscription).filter(
                Subscription.id == subscription_id,
                Subscription.user_id == user_id
            ).first()
            
            if subscription:
                subscription.is_active = False
                session.commit()
                return True
            return False
        finally:
            session.close()

    def get_user_subscriptions(self, user_id: int) -> List[Subscription]:
        """Get all active subscriptions for a user."""
        session = self.get_session()
        try:
            return session.query(Subscription).filter(
                Subscription.user_id == user_id,
                Subscription.is_active == True
            ).all()
        finally:
            session.close()

    def get_subscriptions_by_type(self, subscription_type: str, subscription_id: str) -> List[Subscription]:
        """Get all active subscriptions of a specific type and ID."""
        session = self.get_session()
        try:
            return session.query(Subscription).filter(
                Subscription.subscription_type == subscription_type,
                Subscription.subscription_id == subscription_id,
                Subscription.is_active == True
            ).all()
        finally:
            session.close()

    def save_dataset_snapshot(
        self, 
        dataset_id: str, 
        modified: Optional[str] = None,
        data_processed: Optional[str] = None,
        metadata_processed: Optional[str] = None,
        records_count: int = 0,
        themes: Optional[List[str]] = None
    ) -> DatasetSnapshot:
        """Save dataset snapshot for change detection."""
        session = self.get_session()
        try:
            import json
            snapshot = DatasetSnapshot(
                dataset_id=dataset_id,
                modified=modified,
                data_processed=data_processed,
                metadata_processed=metadata_processed,
                records_count=records_count,
                themes=json.dumps(themes or [])
            )
            session.add(snapshot)
            session.commit()
            session.refresh(snapshot)
            return snapshot
        finally:
            session.close()

    def get_latest_dataset_snapshot(self, dataset_id: str) -> Optional[DatasetSnapshot]:
        """Get the latest snapshot for a dataset."""
        session = self.get_session()
        try:
            return session.query(DatasetSnapshot).filter(
                DatasetSnapshot.dataset_id == dataset_id
            ).order_by(DatasetSnapshot.created_at.desc()).first()
        finally:
            session.close()

    def save_theme_snapshot(self, theme_name: str, dataset_ids: List[str]) -> ThemeSnapshot:
        """Save theme snapshot for change detection."""
        session = self.get_session()
        try:
            import json
            snapshot = ThemeSnapshot(
                theme_name=theme_name,
                dataset_ids=json.dumps(dataset_ids),
                dataset_count=len(dataset_ids)
            )
            session.add(snapshot)
            session.commit()
            session.refresh(snapshot)
            return snapshot
        finally:
            session.close()

    def get_latest_theme_snapshot(self, theme_name: str) -> Optional[ThemeSnapshot]:
        """Get the latest snapshot for a theme."""
        session = self.get_session()
        try:
            return session.query(ThemeSnapshot).filter(
                ThemeSnapshot.theme_name == theme_name
            ).order_by(ThemeSnapshot.created_at.desc()).first()
        finally:
            session.close()

    # Bookmark methods
    def add_bookmark(self, user_id: int, dataset_id: str, dataset_title: str) -> bool:
        """Add bookmark for user. Returns True if added, False if already exists."""
        session = self.get_session()
        try:
            existing = session.query(Bookmark).filter(
                Bookmark.user_id == user_id,
                Bookmark.dataset_id == dataset_id
            ).first()
            
            if existing:
                return False
            
            bookmark = Bookmark(
                user_id=user_id,
                dataset_id=dataset_id,
                dataset_title=dataset_title
            )
            session.add(bookmark)
            session.commit()
            return True
        finally:
            session.close()

    def remove_bookmark(self, user_id: int, dataset_id: str) -> bool:
        """Remove bookmark. Returns True if removed."""
        session = self.get_session()
        try:
            bookmark = session.query(Bookmark).filter(
                Bookmark.user_id == user_id,
                Bookmark.dataset_id == dataset_id
            ).first()
            
            if bookmark:
                session.delete(bookmark)
                session.commit()
                return True
            return False
        finally:
            session.close()

    def get_user_bookmarks(self, user_id: int) -> List[Bookmark]:
        """Get all bookmarks for a user."""
        session = self.get_session()
        try:
            return session.query(Bookmark).filter(
                Bookmark.user_id == user_id
            ).order_by(Bookmark.created_at.desc()).all()
        finally:
            session.close()

    def is_bookmarked(self, user_id: int, dataset_id: str) -> bool:
        """Check if dataset is bookmarked by user."""
        session = self.get_session()
        try:
            bookmark = session.query(Bookmark).filter(
                Bookmark.user_id == user_id,
                Bookmark.dataset_id == dataset_id
            ).first()
            return bookmark is not None
        finally:
            session.close()