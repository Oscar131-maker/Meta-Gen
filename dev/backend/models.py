from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from .database import Base

class DBHistoryItem(Base):
    __tablename__ = "history"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, default="Sin título")
    # Store date as string or datetime. JS sends specific string format, but cleaner to let DB handle time
    # and format on retrieval. However, to match existing frontend expectations mostly,
    # we can store the formatted string or just use DateTime and format in Pydantic.
    # Let's use DateTime for "created_at" and format it on the way out to match the simple string the frontend expects, 
    # or just store the simple string if we want to be lazy.
    # Being professional: Use DateTime.
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    date_str = Column(String) # To store the "12 de enero de 2024" formatted string if we want to keep it simple
    full_input = Column(Text)
    output = Column(Text)
    type = Column(String) # 'url' or 'text'

class DBPromptsConfig(Base):
    __tablename__ = "prompts_config"
    
    id = Column(Integer, primary_key=True) # 1
    openai_system = Column(Text, nullable=True)
    openai_user = Column(Text, nullable=True)
    anthropic_system = Column(Text, nullable=True)
    anthropic_user = Column(Text, nullable=True)
