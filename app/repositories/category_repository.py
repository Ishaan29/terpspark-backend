from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.models.category import Category
import uuid


class CategoryRepository:
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_by_id(self, category_id: str) -> Optional[Category]:
        return self.db.query(Category).filter(Category.id == category_id).first()
    
    def get_by_slug(self, slug: str) -> Optional[Category]:
        return self.db.query(Category).filter(Category.slug == slug).first()
    
    def get_all(self, active_only: bool = True) -> List[Category]:
        query = self.db.query(Category)
        if active_only:
            query = query.filter(Category.is_active == True)
        return query.order_by(Category.name).all()
    
    def create(
        self,
        name: str,
        slug: str,
        color: str,
        description: Optional[str] = None,
        icon: Optional[str] = None
    ) -> Category:
        category_id = str(uuid.uuid4())
        
        category = Category(
            id=category_id,
            name=name,
            slug=slug,
            color=color,
            description=description,
            icon=icon,
            is_active=True
        )
        
        try:
            self.db.add(category)
            self.db.commit()
            self.db.refresh(category)
            return category
        except IntegrityError:
            self.db.rollback()
            raise
    
    def update(self, category: Category, **kwargs) -> Category:
        for key, value in kwargs.items():
            if hasattr(category, key) and key != 'id':
                setattr(category, key, value)
        
        self.db.commit()
        self.db.refresh(category)
        return category
    
    def toggle_active(self, category: Category) -> Category:
        category.is_active = not category.is_active
        self.db.commit()
        self.db.refresh(category)
        return category
    
    def count_events_using_category(self, category_id: str) -> int:
        from app.models.event import Event
        return self.db.query(Event).filter(Event.category_id == category_id).count()

