from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.contrib import messages
from django.http import JsonResponse, HttpResponseRedirect
from django.urls import reverse
from urllib.parse import urlencode
from .models import Course, Evaluation, RubricCell, GroupItemScore, IndividualItemScore, RubricLevel, CourseAssessment, Group


from django.contrib.auth.decorators import login_required

def get_default_period():
    now = timezone.now()
    year = now.year
    month = now.month
    if month in [1, 2]:
        return f"{year}-tav"
    elif month in [3, 4, 5, 6, 7]:
        return f"{year}-1"
    else:
        return f"{year}-2"

@login_required
def index(request):
    # Get all distinct periods from the database
    available_periods = Course.objects.values_list('period', flat=True).distinct().order_by('-period')
    
    # Get the requested period or calculate the default
    selected_period = request.GET.get('period')
    
    if not selected_period:
        default_period = get_default_period()
        # If the calculated default period exists in the db or no periods exist yet, use it.
        # Otherwise, fallback to the latest available period in the db to show something relevant.
        if default_period in available_periods or not available_periods:
            selected_period = default_period
        else:
            selected_period = available_periods[0]
            
    if selected_period == 'all':
        courses = Course.objects.all()
    else:
        courses = Course.objects.filter(period=selected_period)

    context = {
        'courses': courses,
        'available_periods': available_periods,
        'selected_period': selected_period,
    }
    return render(request, 'evaluations/index.html', context)

@login_required
def course_students(request, course_id):
    course = get_object_or_404(Course, pk=course_id)
    students = course.students.all().order_by('last_name_1', 'last_name_2', 'first_names')
    pres_assessments = course.assessments.filter(assessment_type='PRESENTATION')
    exam_assessments = course.assessments.filter(assessment_type='EXAM')
    
    student_data = []
    for student in students:
        group = student.student_groups.filter(course=course).first()
        
        # PRESENTATION logic
        pres_grades = []
        pres_score = 0
        has_all_pres = True
        has_any_pres = False
        
        for assessment in pres_assessments:
            eval_instance = Evaluation.objects.filter(assessment=assessment, evaluated_students=student).first()
            if not eval_instance and group:
                old_eval = Evaluation.objects.filter(assessment=assessment, group=group).first()
                if old_eval and not old_eval.evaluated_students.exists():
                    old_eval.evaluated_students.set(group.members.all())
                    eval_instance = Evaluation.objects.filter(assessment=assessment, evaluated_students=student).first()

            if eval_instance:
                grade = eval_instance.get_student_grade(student)
                pres_grades.append({'assessment': assessment, 'grade': grade})
                pres_score += grade * (assessment.weight_percentage / 100.0)
                has_any_pres = True
            else:
                pres_grades.append({'assessment': assessment, 'grade': None})
                has_all_pres = False
                
        np_grade = round(pres_score, 1) if has_all_pres and pres_assessments.exists() else None
        
        # EXAM logic
        exam_grades = []
        exam_score = 0
        has_all_exam = True
        has_any_exam = False
        
        for assessment in exam_assessments:
            eval_instance = Evaluation.objects.filter(assessment=assessment, evaluated_students=student).first()
            if not eval_instance and group:
                old_eval = Evaluation.objects.filter(assessment=assessment, group=group).first()
                if old_eval and not old_eval.evaluated_students.exists():
                    old_eval.evaluated_students.set(group.members.all())
                    eval_instance = Evaluation.objects.filter(assessment=assessment, evaluated_students=student).first()

            if eval_instance:
                grade = eval_instance.get_student_grade(student)
                exam_grades.append({'assessment': assessment, 'grade': grade})
                exam_score += grade * (assessment.weight_percentage / 100.0)
                has_any_exam = True
            else:
                exam_grades.append({'assessment': assessment, 'grade': None})
                has_all_exam = False
                
        ne_grade = round(exam_score, 1) if has_all_exam and exam_assessments.exists() else None
        
        # EXEMPTION & FINAL GRADE LOGIC
        is_exempt = False
        final_grade = None
        
        if np_grade is not None:
            if course.exemption_grade and np_grade >= course.exemption_grade:
                is_exempt = True
                final_grade = np_grade
            else:
                if ne_grade is not None:
                    # Not exempt, has exam grade
                    final_grade = round((np_grade * (course.presentation_weight / 100.0)) + (ne_grade * (course.exam_weight / 100.0)), 1)
                else:
                    if not exam_assessments.exists():
                        # If the course doesn't even have exams configured
                        final_grade = np_grade
        
        student_data.append({
            'student': student,
            'group': group,
            'pres_grades': pres_grades,
            'np_grade': np_grade,
            'exam_grades': exam_grades,
            'ne_grade': ne_grade,
            'is_exempt': is_exempt,
            'final_grade': final_grade
        })
        
    context = {
        'course': course,
        'pres_assessments': pres_assessments,
        'exam_assessments': exam_assessments,
        'student_data': student_data,
    }
    return render(request, 'evaluations/course_students.html', context)

@login_required
def grade_evaluation(request, eval_id):
    evaluation = get_object_or_404(Evaluation, pk=eval_id)
    assessment = evaluation.assessment
    rubric = assessment.rubric if assessment else None
    group = evaluation.group
    
    if not rubric:
        # Simplistic fallback for direct score
        messages.warning(request, "This evaluation does not have a rubric associated.")
        return redirect('/admin/evaluations/evaluation/')

    # Snapshot logic: use the snapshot of students. If empty (old data), populate it.
    students = evaluation.evaluated_students.all().order_by('last_name_1', 'first_names')
    if not students.exists():
        evaluation.evaluated_students.set(group.members.all())
        students = evaluation.evaluated_students.all().order_by('last_name_1', 'first_names')

    levels = rubric.levels.all()
    items = rubric.items.all()
    cells = RubricCell.objects.filter(item__rubric=rubric)
    
    group_items = items.filter(item_type='GROUP')
    indiv_items = items.filter(item_type='INDIVIDUAL')
    
    if request.method == "POST":
        # Handle Group Scores
        for item in group_items:
            level_id = request.POST.get(f"group_item_{item.id}")
            comment = request.POST.get(f"group_comment_{item.id}", "")
            if level_id:
                level = get_object_or_404(RubricLevel, pk=level_id)
                GroupItemScore.objects.update_or_create(
                    evaluation=evaluation,
                    rubric_item=item,
                    defaults={'level_achieved': level, 'comment': comment}
                )
                
        # Handle Individual Scores
        for student in students:
            for item in indiv_items:
                level_id = request.POST.get(f"indiv_{student.id}_item_{item.id}")
                comment = request.POST.get(f"indiv_{student.id}_comment_{item.id}", "")
                if level_id:
                    level = get_object_or_404(RubricLevel, pk=level_id)
                    IndividualItemScore.objects.update_or_create(
                        evaluation=evaluation,
                        student=student,
                        rubric_item=item,
                        defaults={'level_achieved': level, 'comment': comment}
                    )
        
        evaluation.general_comment = request.POST.get("general_comment", "")
        evaluation.save()
                    
        messages.success(request, f"Grades saved successfully for {group.name}.")
        # Redirect back to the same grading page instead of the dashboard
        return redirect('grade_evaluation', eval_id=evaluation.id)

    # Prepare data for template
    cell_map = {(c.item_id, c.level_id): c.description for c in cells}
    
    # Pre-fetch existing scores to populate the form
    existing_group_scores = {gs.rubric_item_id: gs for gs in evaluation.group_scores.all()}
    existing_indiv_scores = {(is_obj.student_id, is_obj.rubric_item_id): is_obj for is_obj in evaluation.individual_scores.all()}

    matrix_group = []
    for item in group_items:
        row = {'item': item, 'cells': []}
        for level in levels:
            row['cells'].append({
                'level': level,
                'description': cell_map.get((item.id, level.id), ""),
                'is_selected': existing_group_scores.get(item.id) and existing_group_scores[item.id].level_achieved_id == level.id
            })
        row['existing_comment'] = existing_group_scores[item.id].comment if item.id in existing_group_scores else ""
        matrix_group.append(row)
        
    matrix_students = []
    for student in students:
        student_data = {'student': student, 'matrix': []}
        for item in indiv_items:
            row = {'item': item, 'cells': []}
            for level in levels:
                row['cells'].append({
                    'level': level,
                    'description': cell_map.get((item.id, level.id), ""),
                    'is_selected': existing_indiv_scores.get((student.id, item.id)) and existing_indiv_scores[(student.id, item.id)].level_achieved_id == level.id
                })
            row['existing_comment'] = existing_indiv_scores[(student.id, item.id)].comment if (student.id, item.id) in existing_indiv_scores else ""
            student_data['matrix'].append(row)
        matrix_students.append(student_data)

    context = {
        'evaluation': evaluation,
        'group': group,
        'rubric': rubric,
        'levels': levels,
        'matrix_group': matrix_group,
        'matrix_students': matrix_students,
    }
    return render(request, 'evaluations/grade_evaluation.html', context)

from django.http import JsonResponse

@login_required
def grading_dashboard(request):
    courses = Course.objects.all().order_by('-period', 'code')
    context = {
        'courses': courses,
        'auto_course_id': request.GET.get('course_id', ''),
        'auto_assessment_id': request.GET.get('assessment_id', '')
    }
    return render(request, 'evaluations/grading_dashboard.html', context)

@login_required
def api_course_assessments(request, course_id):
    course = get_object_or_404(Course, pk=course_id)
    assessments = course.assessments.all().values('id', 'name', 'assessment_type', 'weight_percentage')
    return JsonResponse({'assessments': list(assessments)})

@login_required
def api_course_groups(request, course_id, assessment_id):
    course = get_object_or_404(Course, pk=course_id)
    assessment = get_object_or_404(CourseAssessment, pk=assessment_id)
    
    groups = course.groups.all().order_by('name')
    data = []
    
    for group in groups:
        # Check if an evaluation already exists for this group and assessment
        eval_instance = Evaluation.objects.filter(assessment=assessment, group=group).first()
        
        members_data = []
        for m in group.members.all().order_by('last_name_1', 'first_names'):
            grade = None
            if eval_instance:
                # If there's an evaluation, we can calculate the grade for this student.
                grade = eval_instance.get_student_grade(m)
            
            members_data.append({
                'name': f"{m.first_names} {m.last_name_1}",
                'grade': round(grade, 1) if grade is not None else None
            })
            
        data.append({
            'id': group.id,
            'name': group.name,
            'members': members_data,
            'is_evaluated': bool(eval_instance),
            'eval_id': eval_instance.id if eval_instance else None
        })
        
    return JsonResponse({'groups': data})

@login_required
def start_grading(request, assessment_id, group_id):
    assessment = get_object_or_404(CourseAssessment, pk=assessment_id)
    group = get_object_or_404(Group, pk=group_id)
    
    # Try to find an existing evaluation
    evaluation = Evaluation.objects.filter(assessment=assessment, group=group).first()
    
    if not evaluation:
        # OPTION A: Create new evaluation and snapshot the students
        evaluation = Evaluation.objects.create(
            assessment=assessment,
            group=group
        )
        # Take the snapshot of current group members
        evaluation.evaluated_students.set(group.members.all())
        
    # Redirect to the interactive grading view
    return redirect('grade_evaluation', eval_id=evaluation.id)
@login_required
def analytics_dashboard(request):
    courses = Course.objects.all().order_by('-period', 'code')
    context = {
        'courses': courses,
    }
    return render(request, 'evaluations/analytics_dashboard.html', context)

@login_required
def analytics_report(request, course_id, assessment_id):
    course = get_object_or_404(Course, pk=course_id)
    assessment = get_object_or_404(CourseAssessment, pk=assessment_id)
    rubric = assessment.rubric
    
    if not rubric:
        return JsonResponse({'error': 'This assessment does not use a rubric.'}, status=400)
        
    items = rubric.items.all()
    group_items = items.filter(item_type='GROUP')
    indiv_items = items.filter(item_type='INDIVIDUAL')
    
    # Get all evaluations for this assessment in this course
    evaluations = Evaluation.objects.filter(assessment=assessment, group__course=course)
    
    # Structure the data grouped by Group -> Students
    # To keep it ordered, we first get the groups
    groups = course.groups.all().order_by('name')
    
    header_groups = []
    header_students = []
    
    # Matrix data structure: list of rows. Each row is dict: {'item': obj, 'scores': [s1, s2...]}
    matrix_group_rows = [{'item': item, 'scores': []} for item in group_items]
    matrix_indiv_rows = [{'item': item, 'scores': []} for item in indiv_items]
    
    # Pre-fetch all scores for fast lookup
    group_scores_dict = {} # (eval_id, item_id): percentage
    indiv_scores_dict = {} # (eval_id, student_id, item_id): percentage
    
    for eval_obj in evaluations:
        for gs in eval_obj.group_scores.all():
            group_scores_dict[(eval_obj.id, gs.rubric_item_id)] = gs.level_achieved.score_percentage
        for ind_s in eval_obj.individual_scores.all():
            indiv_scores_dict[(eval_obj.id, ind_s.student_id, ind_s.rubric_item_id)] = ind_s.level_achieved.score_percentage

    has_data = False

    for group in groups:
        eval_obj = evaluations.filter(group=group).first()
        
        # We only care about students that were evaluated (snapshot) or current members if not evaluated yet but we want to show them?
        # Requirement: "ver el puntaje obtenido". It's better to show the snapshot if evaluated.
        if eval_obj and eval_obj.evaluated_students.exists():
            students = eval_obj.evaluated_students.all().order_by('last_name_1', 'first_names')
            has_data = True
        else:
            students = group.members.all().order_by('last_name_1', 'first_names')
            
        if not students.exists():
            continue
            
        header_groups.append({
            'name': group.name,
            'colspan': students.count()
        })
        
        for student in students:
            header_students.append(student)
            
            # Fill group item rows
            for i, item in enumerate(group_items):
                score = group_scores_dict.get((eval_obj.id, item.id)) if eval_obj else None
                matrix_group_rows[i]['scores'].append(score)
                
            # Fill individual item rows
            for i, item in enumerate(indiv_items):
                score = indiv_scores_dict.get((eval_obj.id, student.id, item.id)) if eval_obj else None
                matrix_indiv_rows[i]['scores'].append(score)

    context = {
        'course': course,
        'assessment': assessment,
        'header_groups': header_groups,
        'header_students': header_students,
        'matrix_group_rows': matrix_group_rows,
        'matrix_indiv_rows': matrix_indiv_rows,
        'has_data': has_data
    }
    
    # Return HTML partial to be injected via AJAX
    return render(request, 'evaluations/partials/analytics_table.html', context)
from django.template.loader import get_template
from django.http import HttpResponse
from xhtml2pdf import pisa
import io

@login_required
def download_feedback_pdf(request, eval_id):
    evaluation = get_object_or_404(Evaluation, pk=eval_id)
    course = evaluation.group.course
    assessment = evaluation.assessment
    rubric = assessment.rubric if assessment else None
    
    if not rubric:
        messages.error(request, "Cannot generate PDF. This evaluation does not have a rubric associated.")
        return redirect('grading_dashboard')
        
    students = evaluation.evaluated_students.all().order_by('last_name_1', 'first_names')
    group_scores = evaluation.group_scores.all()
    indiv_scores = evaluation.individual_scores.all()
    
    # Calculate NP and NE to show final grade logically
    # For a PDF, showing the specific grade for this specific assessment is important.
    # Group grade
    group_grade = evaluation.get_group_score() # Max 100
    group_chilean = evaluation.calculate_chilean_grade(group_grade, max_score=100.0)

    # Student specific grades
    student_data = []
    for student in students:
        student_score = evaluation.get_student_score(student)
        student_chilean = evaluation.get_student_grade(student)
        
        # Collect individual scores for this student
        student_indiv_scores = indiv_scores.filter(student=student)
        
        student_data.append({
            'obj': student,
            'score': student_score,
            'grade': student_chilean,
            'scores': student_indiv_scores
        })

    template_path = 'evaluations/feedback_pdf.html'
    context = {
        'evaluation': evaluation,
        'course': course,
        'assessment': assessment,
        'group': evaluation.group,
        'students': students,
        'student_data': student_data,
        'group_scores': group_scores,
        'group_grade': group_chilean
    }
    
    response = HttpResponse(content_type='application/pdf')
    # Generate filename
    filename = f"Feedback_{course.code}_{assessment.name}_{evaluation.group.name}.pdf".replace(" ", "_")
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    template = get_template(template_path)
    html = template.render(context, request)
    
    # Create PDF
    pisa_status = pisa.CreatePDF(
       html, dest=response
    )
    
    if pisa_status.err:
       return HttpResponse('We had some errors <pre>' + html + '</pre>')
    return response
