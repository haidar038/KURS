from flask_wtf import FlaskForm
from flask_ckeditor import CKEditorField
from wtforms import StringField, SubmitField

class PostForm(FlaskForm):
    title = StringField('Judul')
    body = CKEditorField('Body')
    submit = SubmitField('Posting Artikel')