from django.db import models

class MonitoredRepository(models.Model):
    repo_id = models.IntegerField(unique=True)
    monitored = models.BooleanField(default=False)

    def __str__(self):
        return f"Repository {self.repo_id}: Monitored = {self.monitored}"

class Repository(models.Model):
    # Unfortunately, GitHub's repo_id is not unique, only a combination of owner_name and repo_id is unique
    id = models.AutoField(primary_key=True)
    repo_id = models.IntegerField(unique=True)
    owner_name = models.CharField(max_length=100)
    repo_name = models.CharField(max_length=100)
    monitored = models.BooleanField(default=False)
    translation_in_progress = models.BooleanField(default=False)
    
    # class Meta:
    #     unique_together = ('owner_name', 'repo_id')


class MarkdownFile(models.Model):
    repo = models.ForeignKey(Repository, on_delete=models.CASCADE)
    file_name = models.CharField(max_length=255)
    file_path = models.CharField(max_length=255)
    status = models.CharField(max_length=100)

    class Meta:
        unique_together = ("repo", "file_name", "file_path")


class LastCommit(models.Model):
    repo = models.ForeignKey(Repository, on_delete=models.CASCADE)
    commit_id = models.CharField(max_length=100)
    author = models.CharField(max_length=100)
    message = models.TextField()
    timestamp = models.DateTimeField()

    class Meta:
        unique_together = (('repo', 'commit_id'),)


class PullRequest(models.Model):
    repo = models.OneToOneField(Repository, on_delete=models.CASCADE)
    pull_request_state = models.CharField(max_length=100)
    pull_request_id = models.CharField(max_length=100)

    class Meta:
        unique_together = ("repo",)
