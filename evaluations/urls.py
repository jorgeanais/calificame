from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('course/<int:course_id>/students/', views.course_students, name='course_students'),
    path('evaluation/<int:eval_id>/grade/', views.grade_evaluation, name='grade_evaluation'),
    
    # Grading Dashboard
    path('grading/', views.grading_dashboard, name='grading_dashboard'),
    path('grading/api/assessments/<int:course_id>/', views.api_course_assessments, name='api_course_assessments'),
    path('grading/api/groups/<int:course_id>/<int:assessment_id>/', views.api_course_groups, name='api_course_groups'),
    path('grading/start/<int:assessment_id>/<int:group_id>/', views.start_grading, name='start_grading'),
    # Analytics Dashboard
    path('analytics/', views.analytics_dashboard, name='analytics_dashboard'),
    path('analytics/report/<int:course_id>/<int:assessment_id>/', views.analytics_report, name='analytics_report'),
    
    # PDF Feedback
    path('evaluation/<int:eval_id>/feedback-pdf/', views.download_feedback_pdf, name='download_feedback_pdf'),
]

