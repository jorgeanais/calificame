from django.db import models
from django.core.exceptions import ValidationError
from django.db.models import Sum
from django.utils.translation import gettext_lazy as _

class Course(models.Model):
    name = models.CharField(max_length=200, help_text=_("Course name"))
    code = models.CharField(max_length=50, help_text=_("Course code"))
    section = models.CharField(max_length=50, help_text=_("Course section"))
    period = models.CharField(max_length=50, help_text=_("Academic period (e.g., 2026-1)"))
    
    # Grading structure rules
    presentation_weight = models.FloatField(default=70.0, help_text=_("Weight of the presentation grade (e.g., 70 for 70%)"))
    exam_weight = models.FloatField(default=30.0, help_text=_("Weight of the exam grade (e.g., 30 for 30%)"))
    exemption_grade = models.FloatField(null=True, blank=True, default=5.5, help_text=_("Grade required to be exempted from the exam (e.g., 5.5). Leave blank if exam is mandatory."))

    def __str__(self):
        return f"[{self.period}] {self.code} - {self.name} (Sec {self.section})"

class CourseAssessment(models.Model):
    ASSESSMENT_TYPES = (
        ('PRESENTATION', _('Presentation')),
        ('EXAM', _('Exam')),
    )
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='assessments')
    name = models.CharField(max_length=200, help_text=_("e.g., Entrega 1"))
    assessment_type = models.CharField(max_length=20, choices=ASSESSMENT_TYPES, default='PRESENTATION')
    weight_percentage = models.FloatField(help_text=_("Weight as a percentage (e.g., 30 for 30%)"))
    rubric = models.ForeignKey('Rubric', on_delete=models.SET_NULL, null=True, blank=True, related_name='assessments')

    class Meta:
        ordering = ['assessment_type', 'id']

    def __str__(self):
        return f"{self.name} ({self.weight_percentage}%) [{self.get_assessment_type_display()}]"

class Student(models.Model):
    identification = models.CharField(max_length=50, unique=True, help_text=_("Student ID (RUT, DNI, etc.)"))
    first_names = models.CharField(max_length=100)
    last_name_1 = models.CharField(max_length=100)
    last_name_2 = models.CharField(max_length=100, blank=True, null=True)
    courses = models.ManyToManyField(Course, related_name='students')

    def __str__(self):
        return f"{self.last_name_1} {self.last_name_2 or ''}, {self.first_names} ({self.identification})"

class Group(models.Model):
    name = models.CharField(max_length=100)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='groups')
    members = models.ManyToManyField(Student, related_name='student_groups')

    def __str__(self):
        return f"{self.name} - {self.course.code}"

class Rubric(models.Model):
    name = models.CharField(max_length=200)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='rubrics')
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

class RubricLevel(models.Model):
    rubric = models.ForeignKey(Rubric, on_delete=models.CASCADE, related_name='levels')
    category_name = models.CharField(max_length=50, help_text=_("e.g., MB, B, S"))
    score_percentage = models.FloatField(help_text=_("Value out of 100"))

    class Meta:
        ordering = ['-score_percentage']

    def __str__(self):
        return f"{self.category_name} ({self.score_percentage}%)"

class RubricItem(models.Model):
    ITEM_TYPES = (
        ('GROUP', _('Group')),
        ('INDIVIDUAL', _('Individual')),
    )
    rubric = models.ForeignKey(Rubric, on_delete=models.CASCADE, related_name='items')
    order = models.CharField(max_length=10, help_text=_("e.g., 1A, 2B"))
    description = models.TextField()
    weight = models.FloatField(help_text=_("Weight as a decimal (e.g., 0.10 for 10%)"))
    item_type = models.CharField(max_length=15, choices=ITEM_TYPES, default='GROUP')

    class Meta:
        ordering = ['item_type', 'order']

    def __str__(self):
        return f"[{self.get_item_type_display()}] {self.order} - {self.description[:50]}"

class RubricCell(models.Model):
    item = models.ForeignKey(RubricItem, on_delete=models.CASCADE, related_name='cells')
    level = models.ForeignKey(RubricLevel, on_delete=models.CASCADE, related_name='cells')
    description = models.TextField(blank=True, null=True, help_text=_("Detailed descriptor for this level and item"))

    class Meta:
        unique_together = ['item', 'level']

    def __str__(self):
        return f"Cell: {self.item.order} - {self.level.category_name}"

class Evaluation(models.Model):
    assessment = models.ForeignKey(CourseAssessment, on_delete=models.PROTECT, related_name='evaluations', null=True) # Changed from rubric
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='evaluations')
    date = models.DateField(auto_now_add=True)
    general_comment = models.TextField(blank=True, null=True)
    direct_score = models.FloatField(null=True, blank=True, help_text=_("Score out of 100 (if no rubric is used)"))
    evaluated_students = models.ManyToManyField(Student, related_name='evaluations_participated', blank=True, help_text=_("Students evaluated at the time (snapshot)"))

    def __str__(self):
        assessment_name = self.assessment.name if self.assessment else "Unknown"
        return f"Eval: {self.group.name} - {assessment_name} ({self.date})"
        
    def get_max_possible_score(self):
        """Returns the maximum possible weighted score for this rubric."""
        if not self.assessment or not self.assessment.rubric:
            return 100 # If direct score, max is 100
        
        # Max score is 100 (since levels are percentages out of 100 and items have weights)
        # Assuming weights sum up to 1.0. The total score will be the sum of (weight * 100)
        return 100.0

    def get_group_score(self):
        """Calculate the total group score (only from GROUP items)"""
        if self.direct_score is not None:
            return self.direct_score
            
        score = 0
        for item_score in self.group_scores.all():
            weight = item_score.rubric_item.weight
            level_val = item_score.level_achieved.score_percentage
            score += weight * level_val
        return score
        
    def get_student_score(self, student):
        """Calculate the total score for a specific student (GROUP + INDIVIDUAL)"""
        if self.direct_score is not None:
            return self.direct_score
            
        # Add group score component
        score = 0
        for item_score in self.group_scores.all():
            weight = item_score.rubric_item.weight
            level_val = item_score.level_achieved.score_percentage
            score += weight * level_val
            
        # Add individual score component for this student
        for item_score in self.individual_scores.filter(student=student):
            weight = item_score.rubric_item.weight
            level_val = item_score.level_achieved.score_percentage
            score += weight * level_val
            
        return score

    def calculate_chilean_grade(self, score, max_score=100.0, exigencia=0.6):
        """Converts a score to Chilean scale (1.0 to 7.0) with custom exigencia."""
        if max_score == 0:
            return 1.0
        
        score_exigencia = max_score * exigencia
        
        if score < score_exigencia:
            grade = 3.0 * (score / score_exigencia) + 1.0
        else:
            grade = 3.0 * ((score - score_exigencia) / (max_score * (1 - exigencia))) + 4.0
            
        return round(max(1.0, min(7.0, grade)), 1)
        
    def get_student_grade(self, student):
        """Returns the final grade (1.0-7.0) for a student."""
        score = self.get_student_score(student)
        max_score = self.get_max_possible_score()
        return self.calculate_chilean_grade(score, max_score)

class GroupItemScore(models.Model):
    evaluation = models.ForeignKey(Evaluation, on_delete=models.CASCADE, related_name='group_scores')
    rubric_item = models.ForeignKey(RubricItem, on_delete=models.PROTECT)
    level_achieved = models.ForeignKey(RubricLevel, on_delete=models.PROTECT)
    comment = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.evaluation} - {self.rubric_item.order}"

class IndividualItemScore(models.Model):
    evaluation = models.ForeignKey(Evaluation, on_delete=models.CASCADE, related_name='individual_scores')
    rubric_item = models.ForeignKey(RubricItem, on_delete=models.PROTECT)
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    level_achieved = models.ForeignKey(RubricLevel, on_delete=models.PROTECT)
    comment = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.evaluation} - {self.student.identification} - {self.rubric_item.order}"
