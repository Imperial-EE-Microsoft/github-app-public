from rest_framework import serializers
from .models import LastCommit, Repository, MarkdownFile


class CommitSerializer(serializers.ModelSerializer):
    class Meta:
        model = LastCommit
        fields = "__all__"


class RepositorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Repository
        fields = "__all__"


class MarkdownFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = MarkdownFile
        fields = "__all__"
