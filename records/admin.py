from django.contrib import admin
from models import User, Message, Flood, Report, SpamPattern, Spambot

from django import forms

# Register your models here.
class MessageModelForm(forms.ModelForm):
	#username = forms.CharField()
	body = forms.CharField(widget=forms.Textarea)
	class Meta:
		model = Message
		fields = ["timestamp", "username", "room", "body"]
class MessagesInline(admin.TabularInline):
	model = Message
	form = MessageModelForm
	extra = 1
class UserAdmin(admin.ModelAdmin):
	fieldsets = [
		(None, {'fields':['username', 'creation_date']}),
	]
	inlines = [MessagesInline]
admin.site.register(User, UserAdmin)

class MessageAdmin(admin.ModelAdmin):
	raw_id_fields = ("username",)
	form = MessageModelForm
admin.site.register(Message, MessageAdmin)

class FloodAdmin(admin.ModelAdmin):
	raw_id_fields = ("users", "messages",)
	fields = ["pattern", "timestamp", "room", "users", "messages"]
admin.site.register(Flood, FloodAdmin)

admin.site.register(Report)

class SpamPatternModelForm(forms.ModelForm):
	initial_text_pattern = forms.CharField(widget=forms.Textarea)
	alt_text_pattern = forms.CharField(widget=forms.Textarea)
	link_patterns = forms.CharField(widget=forms.Textarea)
	class Meta:
		model = SpamPattern
		fields = ["name", "initial_text_pattern", "alt_text_pattern", "link_patterns", "young_limit", "old_limit"]

	def __init__(self, *args, **kwargs):
		super(SpamPatternModelForm, self).__init__(*args, **kwargs)
		for key in self.fields:
			self.fields[key].required = False 
class SpamPatternAdmin(admin.ModelAdmin):
	form = SpamPatternModelForm
admin.site.register(SpamPattern, SpamPatternAdmin)

admin.site.register(Spambot)