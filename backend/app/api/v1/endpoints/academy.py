"""
投资者教育中心 API
提供课程学习、测验、进度追踪等功能
"""
from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.onboarding import InvestmentCourse, InvestmentLesson, UserEducationProgress

router = APIRouter()


@router.get("/courses")
async def list_courses(
    category: Optional[str] = Query(None, description="课程分类 (BEGINNER/INTERMEDIATE/ADVANCED)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取课程列表"""
    conditions = [InvestmentCourse.is_published == True]

    if category:
        conditions.append(InvestmentCourse.category == category.upper())

    stmt = select(InvestmentCourse).where(and_(*conditions)).order_by(InvestmentCourse.sort_order)
    result = await db.execute(stmt)
    courses = result.scalars().all()

    # 获取用户的学习进度
    course_ids = [c.id for c in courses]
    progress_stmt = select(UserEducationProgress).where(
        and_(
            UserEducationProgress.user_id == current_user.id,
            UserEducationProgress.course_id.in_(course_ids)
        )
    )
    progress_result = await db.execute(progress_stmt)
    progress_map = {p.course_id: p for p in progress_result.scalars().all()}

    return {
        "status": "success",
        "count": len(courses),
        "courses": [
            {
                "id": c.id,
                "title": c.title,
                "description": c.description,
                "category": c.category,
                "difficulty": c.difficulty,
                "thumbnail_url": c.thumbnail_url,
                "estimated_duration_minutes": c.estimated_duration_minutes,
                "total_lessons": c.total_lessons,
                "total_points": c.total_points,
                "user_progress": {
                    "status": progress_map[c.id].status if c.id in progress_map else "NOT_STARTED",
                    "progress_percent": progress_map[c.id].progress_percent if c.id in progress_map else 0,
                    "completed_at": progress_map[c.id].completed_at.isoformat() if c.id in progress_map and progress_map[c.id].completed_at else None,
                } if c.id in progress_map else None,
            }
            for c in courses
        ],
    }


@router.get("/courses/{course_id}")
async def get_course_detail(
    course_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取课程详情"""
    stmt = select(InvestmentCourse).where(InvestmentCourse.id == course_id)
    result = await db.execute(stmt)
    course = result.scalar_one_or_none()

    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    # 获取课程的所有章节
    lessons_stmt = select(InvestmentLesson).where(
        and_(
            InvestmentLesson.course_id == course_id,
            InvestmentLesson.is_published == True
        )
    ).order_by(InvestmentLesson.sort_order)
    lessons_result = await db.execute(lessons_stmt)
    lessons = lessons_result.scalars().all()

    # 获取用户的学习进度
    progress_stmt = select(UserEducationProgress).where(
        and_(
            UserEducationProgress.user_id == current_user.id,
            UserEducationProgress.course_id == course_id
        )
    )
    progress_result = await db.execute(progress_stmt)
    progress = progress_result.scalars().first()

    return {
        "status": "success",
        "course": {
            "id": course.id,
            "title": course.title,
            "description": course.description,
            "category": course.category,
            "difficulty": course.difficulty,
            "thumbnail_url": course.thumbnail_url,
            "estimated_duration_minutes": course.estimated_duration_minutes,
            "total_lessons": course.total_lessons,
            "total_points": course.total_points,
            "lessons": [
                {
                    "id": l.id,
                    "title": l.title,
                    "estimated_duration_minutes": l.estimated_duration_minutes,
                    "points": l.points,
                    "has_quiz": l.has_quiz,
                    "sort_order": l.sort_order,
                }
                for l in lessons
            ],
            "user_progress": {
                "status": progress.status if progress else "NOT_STARTED",
                "progress_percent": progress.progress_percent if progress else 0,
                "quiz_score": progress.quiz_score if progress else None,
                "quiz_passed": progress.quiz_passed if progress else None,
            } if progress else None,
        },
    }


@router.get("/lessons/{lesson_id}")
async def get_lesson(
    lesson_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取课程内容"""
    stmt = select(InvestmentLesson).where(InvestmentLesson.id == lesson_id)
    result = await db.execute(stmt)
    lesson = result.scalar_one_or_none()

    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")

    # 检查课程是否发布
    course_stmt = select(InvestmentCourse).where(InvestmentCourse.id == lesson.course_id)
    course_result = await db.execute(course_stmt)
    course = course_result.scalar_one_or_none()

    if not course or not course.is_published:
        raise HTTPException(status_code=404, detail="Course not found")

    # 更新或创建学习进度
    progress_stmt = select(UserEducationProgress).where(
        and_(
            UserEducationProgress.user_id == current_user.id,
            UserEducationProgress.lesson_id == lesson_id
        )
    )
    progress_result = await db.execute(progress_stmt)
    progress = progress_result.scalar_one_or_none()

    if not progress:
        progress = UserEducationProgress(
            user_id=current_user.id,
            course_id=lesson.course_id,
            lesson_id=lesson_id,
            status="IN_PROGRESS",
            started_at=datetime.utcnow(),
        )
        db.add(progress)
        await db.commit()
    elif progress.status == "NOT_STARTED":
        progress.status = "IN_PROGRESS"
        progress.started_at = datetime.utcnow()
        await db.commit()

    return {
        "status": "success",
        "lesson": {
            "id": lesson.id,
            "course_id": lesson.course_id,
            "title": lesson.title,
            "content": lesson.content,
            "video_url": lesson.video_url,
            "estimated_duration_minutes": lesson.estimated_duration_minutes,
            "points": lesson.points,
            "has_quiz": lesson.has_quiz,
            "quiz_questions": lesson.quiz_questions if lesson.has_quiz else None,
            "quiz_passing_score": lesson.quiz_passing_score,
        },
    }


@router.post("/lessons/{lesson_id}/complete")
async def complete_lesson(
    lesson_id: str,
    quiz_score: Optional[int] = Query(None, ge=0, le=100, description="测验分数"),
    time_spent_minutes: int = Query(0, ge=0, description="学习时间（分钟）"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """完成课程学习并提交测验"""
    # 获取课程信息
    lesson_stmt = select(InvestmentLesson).where(InvestmentLesson.id == lesson_id)
    lesson_result = await db.execute(lesson_stmt)
    lesson = lesson_result.scalar_one_or_none()

    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")

    # 获取或创建进度
    progress_stmt = select(UserEducationProgress).where(
        and_(
            UserEducationProgress.user_id == current_user.id,
            UserEducationProgress.lesson_id == lesson_id
        )
    )
    progress_result = await db.execute(progress_stmt)
    progress = progress_result.scalar_one_or_none()

    if not progress:
        progress = UserEducationProgress(
            user_id=current_user.id,
            course_id=lesson.course_id,
            lesson_id=lesson_id,
        )
        db.add(progress)

    # 更新进度
    progress.status = "COMPLETED"
    progress.completed_at = datetime.utcnow()
    progress.time_spent_minutes += time_spent_minutes

    if quiz_score is not None and lesson.has_quiz:
        progress.quiz_score = quiz_score
        progress.quiz_passed = quiz_score >= lesson.quiz_passing_score
        progress.quiz_attempts += 1

    progress.progress_percent = 100

    await db.commit()
    await db.refresh(progress)

    return {
        "status": "success",
        "progress": {
            "lesson_id": lesson_id,
            "status": progress.status,
            "quiz_score": progress.quiz_score,
            "quiz_passed": progress.quiz_passed,
            "points_earned": lesson.points if progress.quiz_passed else 0,
        },
    }


@router.get("/progress")
async def get_learning_progress(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取用户的学习进度总览"""
    # 查询用户的进度
    stmt = select(UserEducationProgress).where(UserEducationProgress.user_id == current_user.id)
    result = await db.execute(stmt)
    progress_list = result.scalars().all()

    # 统计数据
    total_courses = len(set(p.course_id for p in progress_list))
    completed_lessons = sum(1 for p in progress_list if p.status == "COMPLETED")
    total_time_spent = sum(p.time_spent_minutes for p in progress_list)
    total_points = 0

    # 计算积分（需要查询对应的课程章节）
    for p in progress_list:
        if p.status == "COMPLETED" and p.quiz_passed:
            lesson_stmt = select(InvestmentLesson).where(InvestmentLesson.id == p.lesson_id)
            lesson_result = await db.execute(lesson_stmt)
            lesson = lesson_result.scalar_one_or_none()
            if lesson:
                total_points += lesson.points

    return {
        "status": "success",
        "progress": {
            "total_courses": total_courses,
            "completed_lessons": completed_lessons,
            "total_time_spent_minutes": total_time_spent,
            "total_points": total_points,
            "lessons": [
                {
                    "lesson_id": p.lesson_id,
                    "course_id": p.course_id,
                    "status": p.status,
                    "progress_percent": p.progress_percent,
                    "quiz_score": p.quiz_score,
                    "quiz_passed": p.quiz_passed,
                }
                for p in progress_list
            ],
        },
    }
