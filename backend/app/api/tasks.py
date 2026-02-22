# backend/app/api/tasks.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from .deps import get_db
from ..models.task import Task

router = APIRouter()

@router.get("/")
async def list_tasks(db: Session = Depends(get_db)):
    """获取所有任务列表"""
    # TODO: 实现任务列表查询逻辑
    return {"message": "Task list endpoint - to be implemented"}

@router.get("/{task_id}")
async def get_task(task_id: int, db: Session = Depends(get_db)):
    """获取单个任务详情"""
    # TODO: 实现任务详情查询逻辑
    return {"message": f"Task detail endpoint for ID {task_id} - to be implemented"}

@router.post("/")
async def create_task(db: Session = Depends(get_db)):
    """创建新任务"""
    # TODO: 实现任务创建逻辑
    return {"message": "Task creation endpoint - to be implemented"}

@router.delete("/{task_id}")
async def delete_task(task_id: int, db: Session = Depends(get_db)):
    """删除任务"""
    # TODO: 实现任务删除逻辑
    return {"message": f"Task deletion endpoint for ID {task_id} - to be implemented"}
