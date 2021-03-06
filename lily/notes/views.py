import anyjson
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseRedirect
from django.utils.translation import ugettext_lazy as _
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView, DeleteView, UpdateView, BaseFormView

from lily.utils.functions import is_ajax
from django.contrib.contenttypes.models import ContentType

from .models import Note
from .forms import NoteForm, UpdateNoteForm, UpdateDateNoteForm


class CreateNoteView(CreateView):
    model = Note
    form_class = NoteForm

    def form_valid(self, form):
        note = form.save(commit=False)
        note.author = self.request.user

        model = self.request.POST['content_type']
        if model not in ['account', 'contact', 'deal', 'case']:
            raise BaseException("Invalid content_type")

        object_id = self.request.POST['object_id']
        content_type = ContentType.objects.get(model=model)
        note.subject = content_type.get_object_for_this_type(id=object_id)
        note.save()
        return CreateView.form_valid(self, form)

    def get_success_url(self):
        """
        Return to the history tab if possible.
        """
        if self.request.META.get('HTTP_REFERER'):
            return '%s#history' % self.request.META.get('HTTP_REFERER')
        else:
            return reverse('dashboard')

from .forms import UpdateNoteForm, NoteForm, UpdateDateNoteForm
from .models import Note


class DeleteNoteView(DeleteView):
    model = Note

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.delete()

        # Show delete message
        message = _('The note was successfully deleted.')
        messages.success(self.request, message)

        if is_ajax(self.request):
            response = anyjson.serialize({
                'error': False,
                'redirect_url': self.get_success_url()
            })
            return HttpResponse(response, content_type='application/json')

        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        """
        Return to the history tab if possible.
        """
        if self.request.META.get('HTTP_REFERER'):
            return '%s#history' % self.request.META.get('HTTP_REFERER')
        else:
            return reverse('dashboard')


class UpdateNoteView(UpdateView):
    model = Note
    form_class = UpdateNoteForm

    def dispatch(self, request, *args, **kwargs):
        """
        For AJAX calls, use a different form and template.
        """
        if is_ajax(request):
            self.template_name_suffix = '_form_ajax'

        return super(UpdateNoteView, self).dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        # Saves the instance
        response = super(UpdateNoteView, self).form_valid(form)

        # Show save message
        message = _('Note has been updated.')
        messages.success(self.request, message)

        if is_ajax(self.request):
            response = anyjson.serialize({
                'error': False,
                'redirect_url': self.get_success_url()
            })
            return HttpResponse(response, content_type='application/json')

        return response

    def form_invalid(self, form):
        response = super(UpdateNoteView, self).form_invalid(form)
        if is_ajax(self.request):
            response = anyjson.serialize({
                'error': True,
                'html': response.rendered_content
            })
            return HttpResponse(response, content_type='application/json')

        return response

    def get_context_data(self, **kwargs):
        kwargs = super(UpdateNoteView, self).get_context_data(**kwargs)
        kwargs.update({
            'note_action': 'note_update',
        })

        return kwargs

    def get_success_url(self):
        """
        Return to the history tab if possible.
        """
        if self.request.META.get('HTTP_REFERER'):
            return '%s#history' % self.request.META.get('HTTP_REFERER')
        else:
            return reverse('dashboard')


class UpdateDateNoteView(UpdateNoteView):
    model = Note
    form_class = UpdateDateNoteForm

    def get_context_data(self, **kwargs):
        kwargs = super(UpdateDateNoteView, self).get_context_data(**kwargs)
        kwargs.update({
            'note_action': 'note_update_date',
        })

        return kwargs


class NoteDetailViewMixin(BaseFormView, DetailView):
    """
    Mix in a NoteForm and list of notes.
    """
    form_class = NoteForm

    def get(self, request, *args, **kwargs):
        # From DetailView
        self.object = self.get_object()

        # From BaseFormView
        form_class = self.get_form_class()
        form = self.get_form(form_class)

        return self.render_to_response(self.get_context_data(form=form))

    def post(self, request, *args, **kwargs):
        # From DetailView
        self.object = self.get_object()

        # From BaseFormView
        form_class = self.get_form_class()
        form = self.get_form(form_class)

        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def form_valid(self, form):
        """
        When adding a note, automatically save the related object and author.
        """
        note = form.save(commit=False)
        note.author = self.request.user
        note.subject = self.object
        note.save()

        return super(NoteDetailViewMixin, self).form_valid(form)

    def get_success_url(self):
        """
        Return to the history tab if possible.
        """
        if self.request.META.get('HTTP_REFERER'):
            return '%s#history' % self.request.META.get('HTTP_REFERER')
        else:
            return reverse('dashboard')


create_note_view = login_required(CreateNoteView.as_view())
delete_note_view = login_required(DeleteNoteView.as_view())
edit_note_view = login_required(UpdateNoteView.as_view())
edit_date_note_view = login_required(UpdateDateNoteView.as_view())
