from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.urls import reverse_lazy
from django.contrib import messages
from django.http import JsonResponse, Http404
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from .models import CertificateTemplate
from .forms import CertificateTemplateForm


class TemplateListView(ListView):
    model = CertificateTemplate
    template_name = 'templates_app/template_list.html'
    context_object_name = 'templates'
    paginate_by = 10

    def get_queryset(self):
        # Optimize by selecting only fields used in template
        return CertificateTemplate.objects.only(
            'id', 'name', 'specialization', 'organization', 'course',
            'template_type', 'is_active'
        )


class TemplateCreateView(CreateView):
    model = CertificateTemplate
    form_class = CertificateTemplateForm
    template_name = 'templates_app/template_form_modal.html'
    success_url = reverse_lazy('templates_app:template_list')

    def form_valid(self, form):
        messages.success(self.request, 'Template created successfully!')
        response = super().form_valid(form)
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'status': 'success', 'id': self.object.id, 'message': 'Template created successfully!'})
        return response

    def form_invalid(self, form):
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)
        return super().form_invalid(form)

    def get(self, request, *args, **kwargs):
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            form = self.get_form()
            return render(request, 'templates_app/template_form_modal.html', {'form': form, 'is_update': False})
        return super().get(request, *args, **kwargs)


class TemplateUpdateView(UpdateView):
    model = CertificateTemplate
    form_class = CertificateTemplateForm
    template_name = 'templates_app/template_form_modal.html'
    success_url = reverse_lazy('templates_app:template_list')

    def form_valid(self, form):
        messages.success(self.request, 'Template updated successfully!')
        response = super().form_valid(form)
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'status': 'success', 'id': self.object.id, 'message': 'Template updated successfully!'})
        return response

    def form_invalid(self, form):
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)
        return super().form_invalid(form)

    def get(self, request, *args, **kwargs):
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            self.object = self.get_object()
            form = self.get_form()
            return render(request, 'templates_app/template_form_modal.html', {'form': form, 'is_update': True})
        return super().get(request, *args, **kwargs)


@method_decorator(csrf_protect, name='dispatch')
class TemplateDeleteView(DeleteView):
    model = CertificateTemplate
    success_url = reverse_lazy('templates_app:template_list')

    def post(self, request, *args, **kwargs):
        try:
            self.object = self.get_object()
        except Http404:
            return JsonResponse({'status': 'error', 'message': 'Template not found!'}, status=404)

        obj_id = self.object.id
        self.object.delete()
        return JsonResponse({'status': 'success', 'id': obj_id, 'message': 'Template deleted successfully!'})


class TemplateDetailView(DetailView):
    model = CertificateTemplate
    template_name = 'templates_app/template_detail_modal.html'
    context_object_name = 'template'

    def get(self, request, *args, **kwargs):
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            self.object = self.get_object()
            context = self.get_context_data(object=self.object)
            return render(request, 'templates_app/template_detail_modal.html', context)
        return super().get(request, *args, **kwargs)
