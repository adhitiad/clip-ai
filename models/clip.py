from sqlalchemy import Column, Integer, String
from utils.db import Base

class Clip(Base):
    __tablename__ = "clips"

    id = Column(Integer, primary_key=True, index=True)
    video_url = Column(String, index=True)
    topic = Column(String)
    start_time = Column(Integer)
    end_time = Column(Integer)
    title_en = Column(String)
    desc_en = Column(String)
    score = Column(Integer, default=0)
    
    # Relationship to user if needed later
    # user_id = Column(Integer, ForeignKey("users.id"))
