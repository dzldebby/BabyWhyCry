from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean, Float, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import enum
import os
from dotenv import load_dotenv

# Load environment variables from config/.env
config_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config')
env_path = os.path.join(config_dir, '.env')
if os.path.exists(env_path):
    load_dotenv(dotenv_path=env_path)

Base = declarative_base()

# Check if we're using PostgreSQL or SQLite
is_postgres = os.getenv("DATABASE_URL") is not None

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    username = Column(String(255), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    role = Column(String(50), default='user')
    department = Column(String(100))
    
    # Relationships
    babies = relationship("Baby", back_populates="parent", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(username='{self.username}', email='{self.email}')>"

class Baby(Base):
    __tablename__ = 'babies'

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    birth_date = Column(DateTime, nullable=True)
    parent_id = Column(Integer, ForeignKey('users.id'))
    
    # Relationships
    parent = relationship("User", back_populates="babies")
    feedings = relationship("Feeding", back_populates="baby", cascade="all, delete-orphan")
    sleeps = relationship("Sleep", back_populates="baby", cascade="all, delete-orphan")
    diapers = relationship("Diaper", back_populates="baby", cascade="all, delete-orphan")
    cryings = relationship("Crying", back_populates="baby", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Baby(name='{self.name}')>"

class FeedingType(enum.Enum):
    BREAST = "breast"
    BOTTLE = "bottle"
    SOLID = "solid"

class Feeding(Base):
    __tablename__ = 'feedings'

    id = Column(Integer, primary_key=True)
    baby_id = Column(Integer, ForeignKey('babies.id'), nullable=False)
    # Use SQLAlchemy Enum type for both PostgreSQL and SQLite
    type = Column(Enum(FeedingType, native_enum=False))
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=True)
    amount = Column(Float, nullable=True)  # in ml or oz
    notes = Column(String(500), nullable=True)
    
    # Relationships
    baby = relationship("Baby", back_populates="feedings")
    
    def __repr__(self):
        return f"<Feeding(type='{self.type}', start_time='{self.start_time}')>"

class Sleep(Base):
    __tablename__ = 'sleeps'

    id = Column(Integer, primary_key=True)
    baby_id = Column(Integer, ForeignKey('babies.id'), nullable=False)
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=True)
    notes = Column(String(500), nullable=True)
    
    # Relationships
    baby = relationship("Baby", back_populates="sleeps")
    
    def __repr__(self):
        return f"<Sleep(start_time='{self.start_time}', end_time='{self.end_time}')>"

class DiaperType(enum.Enum):
    WET = "wet"
    DIRTY = "dirty"
    BOTH = "both"

class Diaper(Base):
    __tablename__ = 'diapers'

    id = Column(Integer, primary_key=True)
    baby_id = Column(Integer, ForeignKey('babies.id'), nullable=False)
    # Use SQLAlchemy Enum type for both PostgreSQL and SQLite
    type = Column(Enum(DiaperType, native_enum=False))
    time = Column(DateTime, default=datetime.utcnow)
    notes = Column(String(500), nullable=True)
    
    # Relationships
    baby = relationship("Baby", back_populates="diapers")
    
    def __repr__(self):
        return f"<Diaper(type='{self.type}', time='{self.time}')>"

class CryingReason(enum.Enum):
    HUNGRY = "hungry"
    DIAPER = "diaper"
    ATTENTION = "attention"
    UNKNOWN = "unknown"

class Crying(Base):
    __tablename__ = 'cryings'

    id = Column(Integer, primary_key=True)
    baby_id = Column(Integer, ForeignKey('babies.id'), nullable=False)
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=True)
    # Use SQLAlchemy Enum type for both PostgreSQL and SQLite
    reason = Column(Enum(CryingReason, native_enum=False), nullable=True)
    predicted_reason = Column(Enum(CryingReason, native_enum=False), nullable=True)
    prediction_confidence = Column(Float, nullable=True)  # 0-100%
    actual_reason = Column(Enum(CryingReason, native_enum=False), nullable=True)  # User feedback
    notes = Column(String(500), nullable=True)
    
    # Relationships
    baby = relationship("Baby", back_populates="cryings")
    
    def __repr__(self):
        return f"<Crying(start_time='{self.start_time}', reason='{self.reason}')>"