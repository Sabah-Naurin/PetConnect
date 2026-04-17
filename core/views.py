from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.contrib import messages
from django.contrib.auth import login
from django.shortcuts import get_object_or_404
from django.contrib.auth.views import LoginView
from .models import BasePetReport, LostReport, SightingReport, AdoptionPost, OwnershipClaim, RescueVerification, MedicalFundRequest, DonationLog, Notification
from .forms import ProfileCreationForm, ProfileUpdateForm
from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.admin.views.decorators import staff_member_required

class CustomLoginView(LoginView):
    template_name = 'sign_in.html'

    def get_success_url(self):
        url = self.get_redirect_url()
        if url:
            return url
        if self.request.user.is_staff or self.request.user.is_superuser:
            return '/admin-panel/'
        return super().get_success_url()

def annotate_reports(reports):
    for report in reports:
        if hasattr(report, 'lost_report'):
            report.report_type = 'Lost'
            report.pet_name = report.lost_report.pet_name
            report.breed = report.lost_report.breed
        elif hasattr(report, 'sighting_report'):
            cond = report.sighting_report.condition.lower()
            if 'injur' in cond or 'sick' in cond or 'rescue' in cond:
                report.report_type = 'Rescue Needed'
            else:
                report.report_type = 'Sighting'
            linked_lost_name = None
            
            approved_claim = report.sighting_report.claims.filter(approval_status='Approved').first()
            if approved_claim:
                linked_lost_name = approved_claim.lost_report.pet_name
            elif getattr(report.sighting_report, 'parent_report_id', None):
                parent_lost = LostReport.objects.filter(id=report.sighting_report.parent_report_id).first()
                if parent_lost:
                    linked_lost_name = parent_lost.pet_name
                    
            if linked_lost_name:
                report.is_sighting_update = True
                report.pet_name = f"Update on {linked_lost_name}"
            else:
                report.is_sighting_update = False
                report.pet_name = f"Unknown {report.primary_color} {report.species}".title()
        elif hasattr(report, 'adoption_post'):
            report.report_type = 'Adoption'
            report.pet_name = report.adoption_post.name
            report.breed = report.adoption_post.breed
        else:
            report.report_type = 'Unknown'
            report.pet_name = 'Unknown Pet'
            report.breed = 'Unknown'
    return reports

def index(request):
    query = request.GET.get('q', '')
    url_name = request.resolver_match.url_name
    from django.db.models import Q
    
    loc = request.GET.get('loc', None)
    if loc is None and request.user.is_authenticated and request.user.location:
        loc = request.user.location

    # N+1 FIX: .select_related() grabs the parent AND all child tables in a single query
    base_qs = BasePetReport.objects.select_related(
        'lost_report', 'sighting_report', 'adoption_post'
    ).filter(is_resolved=False)

    if loc and loc != 'all':
        base_qs = base_qs.filter(location=loc)

    if url_name == 'lost_pets':
        base_qs = base_qs.filter(lost_report__isnull=False)
    elif url_name == 'sightings':
        # Condition should NOT contain rescue/sick/injur to be just a generic sighting
        base_qs = base_qs.filter(sighting_report__isnull=False).exclude(
            Q(sighting_report__condition__icontains='injur') |
            Q(sighting_report__condition__icontains='sick') |
            Q(sighting_report__condition__icontains='rescue')
        )
    elif url_name == 'rescues':
        base_qs = base_qs.filter(
            Q(sighting_report__condition__icontains='injur') |
            Q(sighting_report__condition__icontains='sick') |
            Q(sighting_report__condition__icontains='rescue')
        )
    elif url_name == 'adoptions':
        base_qs = base_qs.filter(adoption_post__isnull=False)

    if query:
        reports = base_qs.filter(
            Q(species__icontains=query) |
            Q(primary_color__icontains=query) |
            Q(location__icontains=query) |
            Q(lost_report__pet_name__icontains=query) |
            Q(lost_report__breed__icontains=query) |
            Q(adoption_post__name__icontains=query) |
            Q(adoption_post__breed__icontains=query)
        ).order_by('-timestamp').distinct()
    else:
        reports = base_qs.order_by('-timestamp')
    
    # Convert queryset to a list to execute the query before passing to annotate_reports
    reports = annotate_reports(list(reports))
            
    return render(request, 'index.html', {'reports': reports})

def signup(request):
    if request.method == 'POST':
        form = ProfileCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Welcome to PetConnect! Account created successfully.")
            return redirect('index')
    else:
        form = ProfileCreationForm()
    return render(request, 'sign_up.html', {'form': form})

@login_required
def post_pet(request):
    if request.method == 'POST':
        report_type = request.POST.get('report_type')
        
        if report_type in ['lost', 'sighting', 'adoption']:
            try:
                with transaction.atomic():
                    base_report = BasePetReport.objects.create(
                        author=request.user,
                        image=request.FILES.get('image'),
                        species=request.POST.get('species'),
                        primary_color=request.POST.get('primary_color'),
                        location=request.POST.get('location'),
                        note=request.POST.get('note')
                    )
                    
                    if report_type == 'lost':
                        LostReport.objects.create(
                            base_report=base_report,
                            pet_name=request.POST.get('pet_name'),
                            breed=request.POST.get('breed'),
                            age=request.POST.get('age_lost'),
                            gender=request.POST.get('gender_lost'),
                            special_marks=request.POST.get('special_marks'),
                            date_lost=request.POST.get('date_lost') or None,
                            time_lost=request.POST.get('time_lost') or None
                        )
                        messages.success(request, "Lost Pet report submitted successfully.")
                    elif report_type == 'sighting':
                        in_custody = request.POST.get('in_custody') == 'True'
                        parent_id = request.POST.get('parent_id')
                        SightingReport.objects.create(
                            base_report=base_report,
                            condition=request.POST.get('condition'),
                            in_custody=in_custody,
                            current_custodian=request.user if in_custody else None,
                            date_sighted=request.POST.get('date_sighted') or None,
                            time_sighted=request.POST.get('time_sighted') or None,
                            parent_report_id=parent_id if parent_id else None
                        )
                        messages.success(request, "Sighting / Rescue report submitted successfully.")
                        
                    elif report_type == 'adoption':
                        AdoptionPost.objects.create(
                            base_report=base_report,
                            owner=request.user,
                            name=request.POST.get('adopt_name'),
                            age=request.POST.get('adopt_age'),
                            gender=request.POST.get('adopt_gender'),
                            breed=request.POST.get('adopt_breed'),
                            vaccination_status=request.POST.get('adopt_vaccine'),
                            sterilization_status=request.POST.get('adopt_sterilization'),
                            food_habit=request.POST.get('adopt_food'),
                            requirements=request.POST.get('adopt_reqs')
                        )
                        messages.success(request, "Adoption post created successfully.")\
                        
            except Exception as e:
                # If anything fails, the database rolls back automatically
                messages.error(request, "There was an error saving your report.")        
            
        return redirect('index')

    parent_id = request.GET.get('parent_id')
    return render(request, 'post_a_pet.html', {'parent_id': parent_id})

def placeholder(request):
    """
    Placeholder view for routes that haven't been connected to full templates yet.
    """
    return render(request, 'base.html')

@login_required
def dashboard(request):
    my_reports = BasePetReport.objects.select_related(
        'lost_report', 'sighting_report', 'adoption_post'
    ).filter(
        Q(author=request.user) | Q(sighting_report__current_custodian=request.user)
    ).distinct().order_by('-timestamp')
    
    notifications = request.user.notifications.filter(is_read=False).order_by('-timestamp')
    
    # Attach DonationLog object to the notification
    for notif in notifications:
        if notif.notif_type == 'DONATION_REVIEW' and notif.related_id:
            notif.donation = DonationLog.objects.filter(id=notif.related_id).first()
    
    my_reports = annotate_reports(list(my_reports))
    
    my_active_reports = [r for r in my_reports if not r.is_resolved]
    my_archived_reports = [r for r in my_reports if r.is_resolved]
            
    context = {
        'my_active_reports': my_active_reports,
        'my_archived_reports': my_archived_reports,
        'notifications': notifications,
    }
    return render(request, 'user_dashboard.html', context)

@login_required
def notifications_view(request):
    # Pull ALL notifications for the historical log page
    notifications = request.user.notifications.all().order_by('-timestamp')
    
    for notif in notifications:
        if notif.notif_type == 'DONATION_REVIEW' and notif.related_id:
            notif.donation = DonationLog.objects.filter(id=notif.related_id).first()
            
    return render(request, 'notifications.html', {'notifications': notifications})


@login_required
@require_POST
def api_mark_notif_read(request, notif_id):
    try:
        notif = Notification.objects.get(id=notif_id, recipient=request.user)
        notif.is_read = True
        notif.save()
        return JsonResponse({'status': 'success'})
    except Notification.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Not found'}, status=404)
    
def report_detail(request, id):
    base_report = get_object_or_404(BasePetReport, id=id)
    report = annotate_reports([base_report])[0]
    
    timeline = []
    if report.report_type == 'Lost':
        sightings = list(SightingReport.objects.filter(parent_report_id=report.lost_report.id).select_related('base_report', 'base_report__author'))
        
        # Also include any sightings formally linked via approved ownership claims
        approved_claims = OwnershipClaim.objects.filter(lost_report=report.lost_report, approval_status='Approved').select_related('sighting_report__base_report', 'sighting_report__base_report__author')
        
        # Ensure distinct sightings to avoid duplicates if somehow they are linked both ways
        seen_sighting_ids = {s.id for s in sightings}
        for claim in approved_claims:
            if claim.sighting_report.id not in seen_sighting_ids:
                sightings.append(claim.sighting_report)
                seen_sighting_ids.add(claim.sighting_report.id)
                
        for s in sightings:
            timeline.append({
                'type': 'sighting',
                'title': 'Sighting Update Added',
                'description': s.base_report.note,
                'author': s.base_report.author,
                'report_id': s.base_report.id,
                'timestamp': s.base_report.timestamp
            })
        
        timeline.append({
            'type': 'lost',
            'title': 'Lost Report Created',
            'description': f"Original post published by {report.author.username}.",
            'author': report.author,
            'timestamp': report.timestamp
        })
        
        timeline.sort(key=lambda x: x['timestamp'], reverse=True)
        
    if request.user.is_authenticated:
        my_lost_pets = LostReport.objects.filter(base_report__author=request.user, base_report__is_resolved=False)
    else:
        my_lost_pets = []
    sighting_update_info = None
    
    if hasattr(report, 'sighting_report'):
        # An Admin approved an Ownership Claim for this sighting
        approved_claim = OwnershipClaim.objects.filter(
            sighting_report=report.sighting_report, 
            approval_status='Approved'
        ).first()
        
        if approved_claim:
            sighting_update_info = {
                'owner_name': approved_claim.owner.username,
                'lost_post_id': approved_claim.lost_report.base_report.id,
                'pet_name': approved_claim.lost_report.pet_name
            }
            
        # Case 2: The user manually linked it using parent_report_id
        elif getattr(report.sighting_report, 'parent_report_id', None):
            parent_lost = LostReport.objects.filter(id=report.sighting_report.parent_report_id).select_related('base_report', 'base_report__author').first()
            
            if parent_lost:
                sighting_update_info = {
                    'owner_name': parent_lost.base_report.author.username,
                    'lost_post_id': parent_lost.base_report.id,
                    'pet_name': parent_lost.pet_name
                }
                
    ml_match_id = request.GET.get('ml_match')
    ml_score = request.GET.get('score')
                
    ml_lost_report = None
    if ml_match_id and ml_score:
        ml_base = BasePetReport.objects.filter(id=ml_match_id, is_resolved=False).first()
        if ml_base and hasattr(ml_base, 'lost_report'):
             ml_lost_report = ml_base.lost_report

    context = {
            'report': report,
            'sighting_update_info': sighting_update_info, 
            'timeline': timeline,                         
            'my_lost_pets': my_lost_pets,                 
            'ml_lost_report': ml_lost_report,
            'ml_score': ml_score,
        }
    
    return render(request, 'report_detail.html', context)

@login_required
def resolve_report(request, id):
    report = get_object_or_404(BasePetReport, id=id)
    
    can_resolve = False
    if request.user == report.author:
        can_resolve = True
    elif hasattr(report, 'sighting_report') and report.sighting_report.in_custody and request.user == report.sighting_report.current_custodian:
        can_resolve = True

    if request.method == 'POST' and can_resolve:
        report.is_resolved = True
        report.save()
        if hasattr(report, 'adoption_post'):
            report.adoption_post.adoption_status = 'Adopted'
            report.adoption_post.save()
        messages.success(request, "Report marked as resolved.")
    return redirect('report_detail', id=id)

@login_required
def settings_view(request):
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Settings updated successfully!")
            return redirect('settings')
    else:
        form = ProfileUpdateForm(instance=request.user)
    
    return render(request, 'settings.html', {'form': form})

@login_required
def claim_ownership(request, id):
    if request.method == 'POST':
        sighting_report = get_object_or_404(SightingReport, base_report_id=id)
        lost_report_id = request.POST.get('lost_report_id')
        claim_type = request.POST.get('claim_type', 'Manual')
        if lost_report_id:
            lost_report = get_object_or_404(LostReport, id=lost_report_id, base_report__author=request.user)
            OwnershipClaim.objects.create(
                sighting_report=sighting_report,
                lost_report=lost_report,
                owner=request.user,
                claim_type=claim_type
            )
            messages.success(request, "Ownership claim submitted and pending verification.")
    return redirect('report_detail', id=id)

@login_required
def op_rescue(request, id):
    if request.method == 'POST':
        sighting_report = get_object_or_404(SightingReport, base_report_id=id)
        if sighting_report.base_report.author == request.user:
            sighting_report.in_custody = True
            sighting_report.current_custodian = request.user
            sighting_report.save()
            messages.success(request, "You have successfully updated the pet's custody status.")
    return redirect('report_detail', id=id)

@login_required
def submit_rescue_verification(request, id):
    sighting_report = get_object_or_404(SightingReport, base_report_id=id)
    if request.method == 'POST':
        proof_image = request.FILES.get('proof_image')
        if proof_image:
            RescueVerification.objects.create(
                sighting=sighting_report,
                rescuer=request.user,
                proof_image=proof_image,
                status='Pending'
            )
            messages.success(request, "Rescue verification submitted. It is pending admin approval.")
            return redirect('report_detail', id=id)
        else:
            messages.error(request, "A proof image is required to claim a rescue.")
    
    return render(request, 'rescue_verification.html', {'report': sighting_report.base_report})

@login_required
def create_fund_request(request, sighting_id):
    sighting = get_object_or_404(SightingReport, id=sighting_id)
    
    # Validation: Must be injured, in custody, and current user must be custodian
    is_injured = 'injur' in sighting.condition.lower() or 'sick' in sighting.condition.lower()
    if not (is_injured and sighting.in_custody and sighting.current_custodian == request.user):
        messages.error(request, "You are not eligible to request funds for this pet.")
        return redirect('report_detail', id=sighting.base_report.id)

    if request.method == 'POST':
        target = request.POST.get('target_amount')
        note = request.POST.get('rescuers_note')
        condition = request.POST.get('current_condition')
        prescription = request.FILES.get('prescription_image')

        MedicalFundRequest.objects.create(
            sighting_report=sighting,
            prescription_image=prescription,
            target_amount=target,
            rescuers_note=note,
            current_condition=condition,
            approval_status='Pending' # Needs Admin to flip this to 'Approved'
        )
        messages.success(request, "Fund request submitted to Admin for verification.")
        return redirect('report_detail', id=sighting.base_report.id)

    return render(request, 'create_fund_request.html', {'sighting': sighting})

def fund_detail(request, fund_id):
    fund = get_object_or_404(MedicalFundRequest, id=fund_id, approval_status='Approved')
    
    # Calculate progress percentage
    if fund.target_amount > 0:
        progress_percent = (fund.current_amount / fund.target_amount) * 100
    else:
        progress_percent = 0

    return render(request, 'fund_detail.html', {
        'fund': fund, 
        'progress_percent': min(progress_percent, 100) # Cap at 100%
    })

@login_required
def submit_donation(request, fund_id):
    if request.method == 'POST':
        fund = get_object_or_404(MedicalFundRequest, id=fund_id)
        amount = request.POST.get('amount')
        trx_id = request.POST.get('trx_id')

        donation = DonationLog.objects.create(
            medical_fund_request=fund,
            donor=request.user,
            amount=amount,
            trx_id=trx_id,
            status='Pending'
        )

        Notification.objects.create(
            recipient=fund.sighting_report.current_custodian,
            notif_type='DONATION_REVIEW',
            related_id=donation.id,
            message=f"New donation of {amount} BDT submitted! Please verify TrxID: {trx_id}",
            link="#"
        )

        messages.success(request, "Donation submitted! It will reflect once the rescuer verifies the transaction.")
    return redirect('fund_detail', fund_id=fund_id)

@login_required
def verify_donation_payment(request, donation_id):
    donation = get_object_or_404(DonationLog, id=donation_id)
    fund = donation.medical_fund_request
    
    # Only the custodian/rescuer can verify the money
    if fund.sighting_report.current_custodian != request.user:
        messages.error(request, "Unauthorized.")
        return redirect('index')

    if request.method == 'POST':
        action = request.POST.get('action') # 'approve' or 'reject'
        
        if action == 'approve' and donation.status == 'Pending':
            with transaction.atomic():
                donation.status = 'Success'
                donation.save()
                # Update the fund total
                fund.current_amount += donation.amount
                fund.save()
                
            # Notify the Donor that their money was received!
            Notification.objects.create(
                recipient=donation.donor,
                notif_type='DONATION_SUCCESS',
                message=f"Your donation of {donation.amount} BDT was verified by the rescuer. Thank you!",
                link=f"/fund/{fund.id}/"
            )
            
            Notification.objects.filter(recipient=request.user, related_id=donation.id, notif_type='DONATION_REVIEW').update(is_read=True)

            messages.success(request, "Donation verified and added to total!")
        else:
            donation.status = 'Rejected'
            donation.save()

            Notification.objects.filter(recipient=request.user, related_id=donation.id, notif_type='DONATION_REVIEW').update(is_read=True)

            messages.info(request, "Donation record rejected.")
            
    return redirect('dashboard')

@staff_member_required
def custom_admin_dashboard(request):
    tab = request.GET.get('tab', 'dashboard')
    
    all_claims = OwnershipClaim.objects.select_related('lost_report', 'sighting_report', 'owner').order_by('-id')
    all_funds = MedicalFundRequest.objects.select_related('sighting_report', 'sighting_report__current_custodian', 'sighting_report__base_report').order_by('-id')
    # FIXED: Query the RescueVerification model directly as per your db schema
    all_rescues = RescueVerification.objects.select_related('sighting', 'sighting__base_report', 'rescuer').order_by('-id')

    pending_claims = all_claims.filter(approval_status='Pending')
    pending_funds = all_funds.filter(approval_status='Pending')
    pending_rescues = all_rescues.filter(status='Pending')

    context = {
        'tab': tab,
        'pending_count': pending_claims.count() + pending_funds.count() + pending_rescues.count() 
    }

    if tab == 'dashboard':
        context['claims_list'] = pending_claims
        context['funds_list'] = pending_funds
        context['rescues_list'] = pending_rescues
    elif tab == 'claims':
        context['claims_list'] = all_claims
    elif tab == 'funds':
        context['funds_list'] = all_funds
    elif tab == 'rescues':
        context['rescues_list'] = all_rescues

    return render(request, 'admin_dashboard.html', context)

@staff_member_required
def verify_rescue(request, rescue_id):
    if request.method == 'POST':
        # FIXED: Use the RescueVerification model
        rescue = get_object_or_404(RescueVerification, id=rescue_id)
        action = request.POST.get('action')
        
        if action == 'approve':
            # Update status to verified and track the admin
            rescue.status = 'Verified'
            rescue.verified_by = request.user
            rescue.save()
            
            # Officially assign custody to the rescuer on the SightingReport
            sighting = rescue.sighting
            sighting.in_custody = True
            sighting.current_custodian = rescue.rescuer
            sighting.save()
            
            # Notify the Rescuer
            Notification.objects.create(
                recipient=rescue.rescuer,
                notif_type='RESCUE_CONFIRMED',
                message=f"Your rescue proof for the {sighting.base_report.species} has been verified. You now have official custody.",
                link=f"/report/{sighting.base_report.id}/"
            )
            messages.success(request, "Rescue verified. Custody confirmed.")
            
        elif action == 'reject':
            # Update status to rejected and track the admin
            rescue.status = 'Rejected'
            rescue.verified_by = request.user
            rescue.save()

            sighting = rescue.sighting
            Notification.objects.create(
                recipient=rescue.rescuer,
                notif_type='RESCUE_REJECTED', 
                message=f"Your rescue proof for the {sighting.base_report.species} could not be verified. Please submit clearer proof.",
                link=f"/report/{sighting.base_report.id}/"
            )
            messages.info(request, "Rescue proof rejected and user notified.")
            
    return redirect('custom_admin_dashboard')

@staff_member_required
def verify_claim(request, claim_id):
    if request.method == 'POST':
        claim = get_object_or_404(OwnershipClaim, id=claim_id)
        action = request.POST.get('action')
        
        if action == 'approve':
            claim.approval_status = 'Approved'
            claim.save()

            Notification.objects.create(
                recipient=claim.owner,
                notif_type='CLAIM_APPROVED',
                message="Your ownership claim has been officially approved.",
                link=f"/report/{claim.lost_report.base_report.id}/"
            )

            Notification.objects.create(
                recipient=claim.sighting_report.base_report.author, 
                notif_type='CLAIM_APPROVED',
                message="The owner of the pet you sighted has been officially verified!",
                link=f"/report/{claim.sighting_report.base_report.id}/"
            )

            messages.success(request, f"Ownership claim for {claim.lost_report.pet_name} approved.")
            
        elif action == 'reject':
            claim.approval_status = 'Rejected'
            claim.save()

            Notification.objects.create(
                recipient=claim.owner,
                notif_type='Ownership Claim Rejected',
                message="Your ownership claim could not be verified. Please submit better proof.",
                link=f"/report/{claim.sighting_report.base_report.id}/"
            )

            messages.info(request, "Ownership claim rejected.")
            
    return redirect('custom_admin_dashboard')

@staff_member_required
def verify_fund(request, fund_id):
    if request.method == 'POST':
        fund = get_object_or_404(MedicalFundRequest, id=fund_id)
        action = request.POST.get('action')
        
        if action == 'approve':
            fund.approval_status = 'Approved'
            fund.save()
            
            # Send notification to the rescuer that their fund is live
            Notification.objects.create(
                recipient=fund.sighting_report.current_custodian,
                notif_type='FUND_ACTIVE',
                message=f"Your medical fund request for {fund.target_amount} BDT has been approved and is now live!",
                link=f"/fund/{fund.id}/"
            )
            messages.success(request, "Fund request approved and is now active.")
            
        elif action == 'reject':
            fund.approval_status = 'Rejected'
            fund.save()
            messages.info(request, "Fund request denied.")
            
    return redirect('custom_admin_dashboard')