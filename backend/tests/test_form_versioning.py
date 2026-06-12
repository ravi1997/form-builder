import pytest
import json
from datetime import datetime, timedelta
from bson import ObjectId
from app import create_app
from app.extensions import mongo
from app.models.form_models import (
    Form, FormCommit, FormSchema, BranchCreateRequest, MergeRequest,
    TagCreateRequest, PublishRequest, MergeConflictResolution
)
from app.services.form_service import FormService
from app.engines.form_engine import (
    create_commit, create_branch, delete_branch, list_branches,
    create_tag, delete_tag, list_tags, publish_branch, get_commit_history,
    get_commit_diff, three_way_merge, find_common_ancestor
)


@pytest.fixture
def app():
    """Create test application."""
    app = create_app()
    app.config['TESTING'] = True
    app.config['MONGODB_URI'] = 'mongodb://localhost:27017/form_builder_test'
    
    with app.app_context():
        yield app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture
def test_user():
    """Create test user."""
    return {
        "_id": ObjectId(),
        "email": "test@example.com",
        "full_name": "Test User",
        "system_role": "user",
        "status": "active",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "is_deleted": False
    }


@pytest.fixture
def test_org():
    """Create test organization."""
    return {
        "_id": ObjectId(),
        "name": "Test Organization",
        "slug": "test-org",
        "status": "active",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "is_deleted": False
    }


@pytest.fixture
def test_project(test_org):
    """Create test project."""
    return {
        "_id": ObjectId(),
        "name": "Test Project",
        "owner_org_id": test_org["_id"],
        "status": "active",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "is_deleted": False
    }


@pytest.fixture
def sample_form_schema():
    """Create sample form schema."""
    return FormSchema(
        ui={
            "theme": {
                "primary_color": "#3B82F6",
                "background_color": "#FFFFFF",
                "font_family": "Inter"
            },
            "layout": "single_page"
        },
        access={
            "type": "org",
            "allowed_org_ids": [],
            "allowed_group_ids": [],
            "allowed_user_ids": [],
            "allow_anonymous": False
        },
        settings={
            "allow_multiple_submissions": False,
            "allow_draft_save": True
        },
        sections=[
            {
                "id": "sec1",
                "title": "Personal Information",
                "description": "Please provide your personal details",
                "repeatable": False,
                "max_repeats": 1,
                "min_repeats": 1,
                "sub_sections": [
                    {
                        "id": "subsec1",
                        "title": "Basic Info",
                        "repeatable": False,
                        "max_repeats": 1,
                        "questions": [
                            {
                                "id": "q1",
                                "type": "text_input",
                                "label": "Full Name",
                                "required": True,
                                "properties": {
                                    "placeholder": "Enter your full name"
                                }
                            },
                            {
                                "id": "q2",
                                "type": "email_input",
                                "label": "Email Address",
                                "required": True,
                                "properties": {
                                    "placeholder": "Enter your email"
                                }
                            }
                        ]
                    }
                ]
            }
        ]
    )


class TestFormVersioning:
    """Test form versioning functionality."""
    
    def test_create_form_with_initial_commit(self, app, test_org, test_project, test_user, sample_form_schema):
        """Test creating a form with initial commit."""
        with app.app_context():
            # Insert test data
            mongo.db.users.insert_one(test_user)
            mongo.db.organisations.insert_one(test_org)
            mongo.db.projects.insert_one(test_project)
            
            # Create form
            result = FormService.create_form(
                org_id=str(test_org["_id"]),
                project_id=str(test_project["_id"]),
                name="Test Form",
                description="A test form for versioning",
                created_by=str(test_user["_id"])
            )
            
            assert result["status"] == "created"
            assert "form_id" in result
            assert "initial_commit_id" in result
            
            # Verify form was created
            form = mongo.db.forms.find_one({"_id": ObjectId(result["form_id"])})
            assert form is not None
            assert form["name"] == "Test Form"
            assert "main" in form["branches"]
            assert form["production_branch"] == "main"
            
            # Verify initial commit was created
            commit = mongo.db.form_commits.find_one({
                "form_id": ObjectId(result["form_id"]),
                "commit_id": result["initial_commit_id"]
            })
            assert commit is not None
            assert commit["message"] == "Initial form creation"
            assert commit["branch"] == "main"
    
    def test_create_branch(self, app, test_org, test_project, test_user, sample_form_schema):
        """Test creating a new branch."""
        with app.app_context():
            # Insert test data
            mongo.db.users.insert_one(test_user)
            mongo.db.organisations.insert_one(test_org)
            mongo.db.projects.insert_one(test_project)
            
            # Create form first
            form_result = FormService.create_form(
                org_id=str(test_org["_id"]),
                project_id=str(test_project["_id"]),
                name="Test Form",
                created_by=str(test_user["_id"])
            )
            
            # Create branch
            branch_request = BranchCreateRequest(
                name="feature-branch",
                from_commit_id=form_result["initial_commit_id"]
            )
            
            result = FormService.create_form_branch(
                form_id=form_result["form_id"],
                branch_data=branch_request,
                user_id=str(test_user["_id"])
            )
            
            assert result["status"] == "created"
            assert result["branch"]["name"] == "feature-branch"
            assert result["branch"]["commit_id"] == form_result["initial_commit_id"]
            
            # Verify branch was created
            form = mongo.db.forms.find_one({"_id": ObjectId(form_result["form_id"])})
            assert "feature-branch" in form["branches"]
    
    def test_list_branches(self, app, test_org, test_project, test_user, sample_form_schema):
        """Test listing form branches."""
        with app.app_context():
            # Insert test data
            mongo.db.users.insert_one(test_user)
            mongo.db.organisations.insert_one(test_org)
            mongo.db.projects.insert_one(test_project)
            
            # Create form first
            form_result = FormService.create_form(
                org_id=str(test_org["_id"]),
                project_id=str(test_project["_id"]),
                name="Test Form",
                created_by=str(test_user["_id"])
            )
            
            # Create additional branch
            branch_request = BranchCreateRequest(
                name="feature-branch",
                from_commit_id=form_result["initial_commit_id"]
            )
            
            FormService.create_form_branch(
                form_id=form_result["form_id"],
                branch_data=branch_request,
                user_id=str(test_user["_id"])
            )
            
            # List branches
            branches = FormService.list_form_branches(
                form_id=form_result["form_id"],
                user_id=str(test_user["_id"])
            )
            
            assert len(branches) == 2
            branch_names = [b["name"] for b in branches]
            assert "main" in branch_names
            assert "feature-branch" in branch_names
    
    def test_delete_branch(self, app, test_org, test_project, test_user, sample_form_schema):
        """Test deleting a branch."""
        with app.app_context():
            # Insert test data
            mongo.db.users.insert_one(test_user)
            mongo.db.organisations.insert_one(test_org)
            mongo.db.projects.insert_one(test_project)
            
            # Create form first
            form_result = FormService.create_form(
                org_id=str(test_org["_id"]),
                project_id=str(test_project["_id"]),
                name="Test Form",
                created_by=str(test_user["_id"])
            )
            
            # Create additional branch
            branch_request = BranchCreateRequest(
                name="feature-branch",
                from_commit_id=form_result["initial_commit_id"]
            )
            
            FormService.create_form_branch(
                form_id=form_result["form_id"],
                branch_data=branch_request,
                user_id=str(test_user["_id"])
            )
            
            # Delete branch
            delete_request = BranchDeleteRequest(branch_name="feature-branch")
            result = FormService.delete_form_branch(
                form_id=form_result["form_id"],
                branch_data=delete_request,
                user_id=str(test_user["_id"])
            )
            
            assert result["status"] == "deleted"
            
            # Verify branch was deleted
            form = mongo.db.forms.find_one({"_id": ObjectId(form_result["form_id"])})
            assert "feature-branch" not in form["branches"]
    
    def test_create_tag(self, app, test_org, test_project, test_user, sample_form_schema):
        """Test creating a tag."""
        with app.app_context():
            # Insert test data
            mongo.db.users.insert_one(test_user)
            mongo.db.organisations.insert_one(test_org)
            mongo.db.projects.insert_one(test_project)
            
            # Create form first
            form_result = FormService.create_form(
                org_id=str(test_org["_id"]),
                project_id=str(test_project["_id"]),
                name="Test Form",
                created_by=str(test_user["_id"])
            )
            
            # Create tag
            tag_request = TagCreateRequest(
                tag_name="v1.0",
                commit_id=form_result["initial_commit_id"],
                message="Initial version release"
            )
            
            result = FormService.create_form_tag(
                form_id=form_result["form_id"],
                tag_data=tag_request,
                user_id=str(test_user["_id"])
            )
            
            assert result["status"] == "created"
            assert result["tag"]["tag"] == "v1.0"
            assert result["tag"]["commit_id"] == form_result["initial_commit_id"]
            
            # Verify tag was created
            form = mongo.db.forms.find_one({"_id": ObjectId(form_result["form_id"])})
            assert "v1.0" in form["tags"]
            
            # Verify commit has tag
            commit = mongo.db.form_commits.find_one({
                "form_id": ObjectId(form_result["form_id"]),
                "commit_id": form_result["initial_commit_id"]
            })
            assert commit["tag"] == "v1.0"
    
    def test_list_tags(self, app, test_org, test_project, test_user, sample_form_schema):
        """Test listing form tags."""
        with app.app_context():
            # Insert test data
            mongo.db.users.insert_one(test_user)
            mongo.db.organisations.insert_one(test_org)
            mongo.db.projects.insert_one(test_project)
            
            # Create form first
            form_result = FormService.create_form(
                org_id=str(test_org["_id"]),
                project_id=str(test_project["_id"]),
                name="Test Form",
                created_by=str(test_user["_id"])
            )
            
            # Create multiple tags
            tag_request1 = TagCreateRequest(
                tag_name="v1.0",
                commit_id=form_result["initial_commit_id"]
            )
            
            tag_request2 = TagCreateRequest(
                tag_name="v1.1",
                commit_id=form_result["initial_commit_id"]
            )
            
            FormService.create_form_tag(
                form_id=form_result["form_id"],
                tag_data=tag_request1,
                user_id=str(test_user["_id"])
            )
            
            FormService.create_form_tag(
                form_id=form_result["form_id"],
                tag_data=tag_request2,
                user_id=str(test_user["_id"])
            )
            
            # List tags
            tags = FormService.list_form_tags(
                form_id=form_result["form_id"],
                user_id=str(test_user["_id"])
            )
            
            assert len(tags) == 2
            tag_names = [t["name"] for t in tags]
            assert "v1.0" in tag_names
            assert "v1.1" in tag_names
    
    def test_publish_branch(self, app, test_org, test_project, test_user, sample_form_schema):
        """Test publishing a branch."""
        with app.app_context():
            # Insert test data
            mongo.db.users.insert_one(test_user)
            mongo.db.organisations.insert_one(test_org)
            mongo.db.projects.insert_one(test_project)
            
            # Create form first
            form_result = FormService.create_form(
                org_id=str(test_org["_id"]),
                project_id=str(test_project["_id"]),
                name="Test Form",
                created_by=str(test_user["_id"])
            )
            
            # Create additional branch
            branch_request = BranchCreateRequest(
                name="feature-branch",
                from_commit_id=form_result["initial_commit_id"]
            )
            
            FormService.create_form_branch(
                form_id=form_result["form_id"],
                branch_data=branch_request,
                user_id=str(test_user["_id"])
            )
            
            # Publish branch
            publish_request = PublishRequest(
                branch_name="feature-branch",
                message="Publish feature branch to production"
            )
            
            result = FormService.publish_form_branch(
                form_id=form_result["form_id"],
                publish_data=publish_request,
                user_id=str(test_user["_id"])
            )
            
            assert result["status"] == "published"
            assert result["publication"]["production_branch"] == "feature-branch"
            
            # Verify production branch was updated
            form = mongo.db.forms.find_one({"_id": ObjectId(form_result["form_id"])})
            assert form["production_branch"] == "feature-branch"
    
    def test_merge_branches_no_conflict(self, app, test_org, test_project, test_user, sample_form_schema):
        """Test merging branches without conflicts."""
        with app.app_context():
            # Insert test data
            mongo.db.users.insert_one(test_user)
            mongo.db.organisations.insert_one(test_org)
            mongo.db.projects.insert_one(test_project)
            
            # Create form first
            form_result = FormService.create_form(
                org_id=str(test_org["_id"]),
                project_id=str(test_project["_id"]),
                name="Test Form",
                created_by=str(test_user["_id"])
            )
            
            # Create feature branch
            branch_request = BranchCreateRequest(
                name="feature-branch",
                from_commit_id=form_result["initial_commit_id"]
            )
            
            FormService.create_form_branch(
                form_id=form_result["form_id"],
                branch_data=branch_request,
                user_id=str(test_user["_id"])
            )
            
            # Update schema on feature branch
            updated_schema = sample_form_schema.dict()
            updated_schema["ui"]["theme"]["primary_color"] = "#FF0000"
            
            FormService.update_form_schema(
                form_id=form_result["form_id"],
                schema=updated_schema,
                user_id=str(test_user["_id"]),
                message="Update primary color",
                branch="feature-branch"
            )
            
            # Merge feature branch back to main
            merge_request = MergeRequest(
                source_branch="feature-branch",
                target_branch="main"
            )
            
            result = FormService.merge_form_branches(
                form_id=form_result["form_id"],
                merge_data=merge_request,
                user_id=str(test_user["_id"])
            )
            
            assert result["result"]["status"] == "merged"
            assert "commit_id" in result["result"]
    
    def test_merge_branches_with_conflict(self, app, test_org, test_project, test_user, sample_form_schema):
        """Test merging branches with conflicts."""
        with app.app_context():
            # Insert test data
            mongo.db.users.insert_one(test_user)
            mongo.db.organisations.insert_one(test_org)
            mongo.db.projects.insert_one(test_project)
            
            # Create form first
            form_result = FormService.create_form(
                org_id=str(test_org["_id"]),
                project_id=str(test_project["_id"]),
                name="Test Form",
                created_by=str(test_user["_id"])
            )
            
            # Create feature branch
            branch_request = BranchCreateRequest(
                name="feature-branch",
                from_commit_id=form_result["initial_commit_id"]
            )
            
            FormService.create_form_branch(
                form_id=form_result["form_id"],
                branch_data=branch_request,
                user_id=str(test_user["_id"])
            )
            
            # Update schema on main branch
            updated_schema_main = sample_form_schema.dict()
            updated_schema_main["ui"]["theme"]["primary_color"] = "#FF0000"
            
            FormService.update_form_schema(
                form_id=form_result["form_id"],
                schema=updated_schema_main,
                user_id=str(test_user["_id"]),
                message="Update primary color on main",
                branch="main"
            )
            
            # Update schema on feature branch with conflicting change
            updated_schema_feature = sample_form_schema.dict()
            updated_schema_feature["ui"]["theme"]["primary_color"] = "#00FF00"
            
            FormService.update_form_schema(
                form_id=form_result["form_id"],
                schema=updated_schema_feature,
                user_id=str(test_user["_id"]),
                message="Update primary color on feature",
                branch="feature-branch"
            )
            
            # Try to merge - should create conflict
            merge_request = MergeRequest(
                source_branch="feature-branch",
                target_branch="main"
            )
            
            result = FormService.merge_form_branches(
                form_id=form_result["form_id"],
                merge_data=merge_request,
                user_id=str(test_user["_id"])
            )
            
            assert result["result"]["status"] == "conflict"
            assert "conflict_fields" in result["result"]
            assert len(result["result"]["conflict_fields"]) > 0
    
    def test_get_commit_history(self, app, test_org, test_project, test_user, sample_form_schema):
        """Test getting commit history."""
        with app.app_context():
            # Insert test data
            mongo.db.users.insert_one(test_user)
            mongo.db.organisations.insert_one(test_org)
            mongo.db.projects.insert_one(test_project)
            
            # Create form first
            form_result = FormService.create_form(
                org_id=str(test_org["_id"]),
                project_id=str(test_project["_id"]),
                name="Test Form",
                created_by=str(test_user["_id"])
            )
            
            # Make multiple commits
            for i in range(3):
                updated_schema = sample_form_schema.dict()
                updated_schema["ui"]["theme"]["primary_color"] = f"#FF{i}00"
                
                FormService.update_form_schema(
                    form_id=form_result["form_id"],
                    schema=updated_schema,
                    user_id=str(test_user["_id"]),
                    message=f"Commit {i+1}"
                )
            
            # Get commit history
            commits = FormService.get_form_commit_history(
                form_id=form_result["form_id"],
                user_id=str(test_user["_id"])
            )
            
            assert len(commits) >= 4  # Initial + 3 updates
            assert commits[0]["message"] == "Commit 3"  # Most recent first
            assert commits[-1]["message"] == "Initial form creation"
    
    def test_get_commit_diff(self, app, test_org, test_project, test_user, sample_form_schema):
        """Test getting commit differences."""
        with app.app_context():
            # Insert test data
            mongo.db.users.insert_one(test_user)
            mongo.db.organisations.insert_one(test_org)
            mongo.db.projects.insert_one(test_project)
            
            # Create form first
            form_result = FormService.create_form(
                org_id=str(test_org["_id"]),
                project_id=str(test_project["_id"]),
                name="Test Form",
                created_by=str(test_user["_id"])
            )
            
            # Make a commit with changes
            updated_schema = sample_form_schema.dict()
            updated_schema["ui"]["theme"]["primary_color"] = "#FF0000"
            
            update_result = FormService.update_form_schema(
                form_id=form_result["form_id"],
                schema=updated_schema,
                user_id=str(test_user["_id"]),
                message="Update primary color"
            )
            
            # Get diff between commits
            diff = FormService.get_form_commit_diff(
                form_id=form_result["form_id"],
                commit_a_id=form_result["initial_commit_id"],
                commit_b_id=update_result["commit_id"],
                user_id=str(test_user["_id"])
            )
            
            assert "modifications" in diff
            assert len(diff["modifications"]) > 0
    
    def test_resolve_merge_conflict(self, app, test_org, test_project, test_user, sample_form_schema):
        """Test resolving merge conflicts."""
        with app.app_context():
            # Insert test data
            mongo.db.users.insert_one(test_user)
            mongo.db.organisations.insert_one(test_org)
            mongo.db.projects.insert_one(test_project)
            
            # Create form first
            form_result = FormService.create_form(
                org_id=str(test_org["_id"]),
                project_id=str(test_project["_id"]),
                name="Test Form",
                created_by=str(test_user["_id"])
            )
            
            # Create feature branch
            branch_request = BranchCreateRequest(
                name="feature-branch",
                from_commit_id=form_result["initial_commit_id"]
            )
            
            FormService.create_form_branch(
                form_id=form_result["form_id"],
                branch_data=branch_request,
                user_id=str(test_user["_id"])
            )
            
            # Create conflicting changes
            updated_schema_main = sample_form_schema.dict()
            updated_schema_main["ui"]["theme"]["primary_color"] = "#FF0000"
            
            FormService.update_form_schema(
                form_id=form_result["form_id"],
                schema=updated_schema_main,
                user_id=str(test_user["_id"]),
                message="Update primary color on main",
                branch="main"
            )
            
            updated_schema_feature = sample_form_schema.dict()
            updated_schema_feature["ui"]["theme"]["primary_color"] = "#00FF00"
            
            FormService.update_form_schema(
                form_id=form_result["form_id"],
                schema=updated_schema_feature,
                user_id=str(test_user["_id"]),
                message="Update primary color on feature",
                branch="feature-branch"
            )
            
            # Create conflict
            merge_request = MergeRequest(
                source_branch="feature-branch",
                target_branch="main"
            )
            
            conflict_result = FormService.merge_form_branches(
                form_id=form_result["form_id"],
                merge_data=merge_request,
                user_id=str(test_user["_id"])
            )
            
            assert conflict_result["result"]["status"] == "conflict"
            
            # Get pending merges
            pending_merges = FormService.get_pending_merges(
                form_id=form_result["form_id"],
                user_id=str(test_user["_id"])
            )
            
            assert len(pending_merges) == 1
            
            # Resolve conflict
            resolution_data = MergeConflictResolution(
                pending_merge_id=ObjectId(pending_merges[0]["id"]),
                resolved_fields={"ui.theme.primary_color": "#0000FF"},
                resolution_strategy="manual"
            )
            
            resolve_result = FormService.resolve_merge_conflict(
                form_id=form_result["form_id"],
                resolution_data=resolution_data,
                user_id=str(test_user["_id"])
            )
            
            assert resolve_result["status"] == "resolved"
            assert "commit_id" in resolve_result["resolution"]


class TestFormVersioningAPI:
    """Test form versioning API endpoints."""
    
    def test_create_form_api(self, client, test_user, test_org, test_project):
        """Test creating form via API."""
        with client.application.app_context():
            # Insert test data
            mongo.db.users.insert_one(test_user)
            mongo.db.organisations.insert_one(test_org)
            mongo.db.projects.insert_one(test_project)
            
            # Create form
            response = client.post('/api/internal/v1/forms', json={
                "name": "Test Form API",
                "description": "Test form created via API",
                "org_id": str(test_org["_id"]),
                "project_id": str(test_project["_id"])
            })
            
            assert response.status_code == 201
            data = response.get_json()
            assert data["status"] == "success"
            assert "form_id" in data["data"]
    
    def test_get_form_api(self, client, test_user, test_org, test_project):
        """Test getting form via API."""
        with client.application.app_context():
            # Insert test data
            mongo.db.users.insert_one(test_user)
            mongo.db.organisations.insert_one(test_org)
            mongo.db.projects.insert_one(test_project)
            
            # Create form first
            form_result = FormService.create_form(
                org_id=str(test_org["_id"]),
                project_id=str(test_project["_id"]),
                name="Test Form",
                created_by=str(test_user["_id"])
            )
            
            # Get form
            response = client.get(f'/api/internal/v1/forms/{form_result["form_id"]}')
            
            assert response.status_code == 200
            data = response.get_json()
            assert data["status"] == "success"
            assert data["data"]["name"] == "Test Form"
    
    def test_create_branch_api(self, client, test_user, test_org, test_project):
        """Test creating branch via API."""
        with client.application.app_context():
            # Insert test data
            mongo.db.users.insert_one(test_user)
            mongo.db.organisations.insert_one(test_org)
            mongo.db.projects.insert_one(test_project)
            
            # Create form first
            form_result = FormService.create_form(
                org_id=str(test_org["_id"]),
                project_id=str(test_project["_id"]),
                name="Test Form",
                created_by=str(test_user["_id"])
            )
            
            # Create branch
            response = client.post(f'/api/internal/v1/forms/{form_result["form_id"]}/branches', json={
                "name": "api-feature-branch",
                "from_commit_id": form_result["initial_commit_id"]
            })
            
            assert response.status_code == 201
            data = response.get_json()
            assert data["status"] == "success"
            assert data["data"]["branch"]["name"] == "api-feature-branch"
    
    def test_merge_branches_api(self, client, test_user, test_org, test_project):
        """Test merging branches via API."""
        with client.application.app_context():
            # Insert test data
            mongo.db.users.insert_one(test_user)
            mongo.db.organisations.insert_one(test_org)
            mongo.db.projects.insert_one(test_project)
            
            # Create form first
            form_result = FormService.create_form(
                org_id=str(test_org["_id"]),
                project_id=str(test_project["_id"]),
                name="Test Form",
                created_by=str(test_user["_id"])
            )
            
            # Create feature branch
            client.post(f'/api/internal/v1/forms/{form_result["form_id"]}/branches', json={
                "name": "api-feature-branch",
                "from_commit_id": form_result["initial_commit_id"]
            })
            
            # Try to merge (should succeed without conflicts)
            response = client.post(f'/api/internal/v1/forms/{form_result["form_id"]}/merge', json={
                "source_branch": "api-feature-branch",
                "target_branch": "main"
            })
            
            assert response.status_code == 200
            data = response.get_json()
            assert data["status"] == "success"
            assert data["data"]["result"]["status"] == "merged"


class TestFormVersioningEngine:
    """Test form versioning engine functions."""
    
    def test_find_common_ancestor(self, app, test_org, test_project, test_user):
        """Test finding common ancestor between commits."""
        with app.app_context():
            # Insert test data
            mongo.db.users.insert_one(test_user)
            mongo.db.organisations.insert_one(test_org)
            mongo.db.projects.insert_one(test_project)
            
            # Create form first
            form_result = FormService.create_form(
                org_id=str(test_org["_id"]),
                project_id=str(test_project["_id"]),
                name="Test Form",
                created_by=str(test_user["_id"])
            )
            
            # Create feature branch
            branch_request = BranchCreateRequest(
                name="feature-branch",
                from_commit_id=form_result["initial_commit_id"]
            )
            
            FormService.create_form_branch(
                form_id=form_result["form_id"],
                branch_data=branch_request,
                user_id=str(test_user["_id"])
            )
            
            # Make commits on both branches
            main_commit = FormService.update_form_schema(
                form_id=form_result["form_id"],
                schema={"ui": {"theme": {"primary_color": "#FF0000"}}},
                user_id=str(test_user["_id"]),
                message="Update main branch",
                branch="main"
            )
            
            feature_commit = FormService.update_form_schema(
                form_id=form_result["form_id"],
                schema={"ui": {"theme": {"primary_color": "#00FF00"}}},
                user_id=str(test_user["_id"]),
                message="Update feature branch",
                branch="feature-branch"
            )
            
            # Find common ancestor
            common_ancestor = find_common_ancestor(
                form_id=ObjectId(form_result["form_id"]),
                commit_a_id=main_commit["commit_id"],
                commit_b_id=feature_commit["commit_id"]
            )
            
            assert common_ancestor == form_result["initial_commit_id"]
    
    def test_get_commit_diff_engine(self, app, test_org, test_project, test_user):
        """Test getting commit diff via engine."""
        with app.app_context():
            # Insert test data
            mongo.db.users.insert_one(test_user)
            mongo.db.organisations.insert_one(test_org)
            mongo.db.projects.insert_one(test_project)
            
            # Create form first
            form_result = FormService.create_form(
                org_id=str(test_org["_id"]),
                project_id=str(test_project["_id"]),
                name="Test Form",
                created_by=str(test_user["_id"])
            )
            
            # Make a commit with changes
            updated_schema = {
                "ui": {
                    "theme": {
                        "primary_color": "#FF0000"
                    }
                },
                "access": {
                    "type": "org"
                },
                "settings": {},
                "sections": []
            }
            
            update_result = FormService.update_form_schema(
                form_id=form_result["form_id"],
                schema=updated_schema,
                user_id=str(test_user["_id"]),
                message="Update primary color"
            )
            
            # Get diff via engine
            diff = get_commit_diff(
                form_id=ObjectId(form_result["form_id"]),
                commit_a_id=form_result["initial_commit_id"],
                commit_b_id=update_result["commit_id"]
            )
            
            assert "modifications" in diff
            assert len(diff["modifications"]) > 0


if __name__ == '__main__':
    pytest.main([__file__])