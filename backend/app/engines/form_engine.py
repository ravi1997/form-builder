import hashlib
import datetime
from bson import ObjectId
from app.extensions import mongo

def generate_commit_id(form_id, timestamp, author_id):
    raw_str = f"{str(form_id)}{str(timestamp)}{str(author_id)}"
    return hashlib.sha256(raw_str.encode("utf-8")).hexdigest()[:12]

def create_commit(form_id, schema, author_id, message, branch, parent_ids=None):
    if parent_ids is None:
        parent_ids = []
    timestamp = datetime.datetime.utcnow().isoformat()
    commit_id = generate_commit_id(form_id, timestamp, author_id)

    fid = ObjectId(form_id) if isinstance(form_id, str) and ObjectId.is_valid(form_id) else form_id
    uid = ObjectId(author_id) if isinstance(author_id, str) and ObjectId.is_valid(author_id) else author_id

    form_doc = mongo.db.forms.find_one({"_id": fid, "is_deleted": False})
    if not form_doc:
        raise ValueError(f"Form {form_id} not found")

    if "branches" not in form_doc:
        raise ValueError(f"Form {form_id} has no branch registry")

    if parent_ids:
        for parent_id in parent_ids:
            parent_commit = mongo.db.form_commits.find_one(
                {"form_id": fid, "commit_id": parent_id}
            )
            if not parent_commit:
                raise ValueError(f"Parent commit {parent_id} not found for form {form_id}")
    elif branch in form_doc["branches"]:
        branch_head = form_doc["branches"].get(branch)
        if branch_head:
            parent_ids = [branch_head]

    commit_doc = {
        "form_id": fid,
        "commit_id": commit_id,
        "parent_ids": parent_ids,
        "author_id": uid,
        "message": message,
        "branch": branch,
        "timestamp": timestamp,
        "schema": schema
    }
    
    mongo.db.form_commits.insert_one(commit_doc)
    
    # Update branch HEAD in forms collection
    mongo.db.forms.update_one(
        {"_id": fid, "is_deleted": False},
        {
            "$set": {
                f"branches.{branch}": commit_id,
                "updated_at": timestamp
            }
        }
    )
    
    return commit_doc

def create_branch(form_id, name, from_commit_id):
    fid = ObjectId(form_id) if isinstance(form_id, str) and ObjectId.is_valid(form_id) else form_id
    
    # Check if branch already exists in form
    form = mongo.db.forms.find_one({"_id": fid, "is_deleted": False})
    if not form:
        raise ValueError(f"Form {form_id} not found")
        
    if "branches" in form and name in form["branches"]:
        raise ValueError(f"Branch {name} already exists for form {form_id}")
        
    # Verify commit exists
    commit = mongo.db.form_commits.find_one({"form_id": fid, "commit_id": from_commit_id})
    if not commit:
        raise ValueError(f"Commit {from_commit_id} not found for form {form_id}")
        
    # Update branch in forms collection
    mongo.db.forms.update_one(
        {"_id": fid, "is_deleted": False},
        {"$set": {f"branches.{name}": from_commit_id, "updated_at": datetime.datetime.utcnow().isoformat()}}
    )
    
    return {"name": name, "commit_id": from_commit_id}

def find_common_ancestor(form_id, commit_a_id, commit_b_id):
    fid = ObjectId(form_id) if isinstance(form_id, str) and ObjectId.is_valid(form_id) else form_id
    
    def get_parents(cid):
        c = mongo.db.form_commits.find_one({"form_id": fid, "commit_id": cid})
        return c.get("parent_ids", []) if c else []
        
    ancestors_a = set()
    queue = [commit_a_id]
    while queue:
        curr = queue.pop(0)
        if curr not in ancestors_a:
            ancestors_a.add(curr)
            queue.extend(get_parents(curr))
            
    queue = [commit_b_id]
    visited_b = set()
    while queue:
        curr = queue.pop(0)
        if curr in ancestors_a:
            return curr
        if curr not in visited_b:
            visited_b.add(curr)
            queue.extend(get_parents(curr))
            
    return None

def index_schema_elements(schema):
    sections = {}
    sub_sections = {}
    questions = {}
    
    if not schema:
        return sections, sub_sections, questions
        
    for sec in schema.get("sections", []):
        sec_id = sec.get("id")
        if sec_id:
            sections[sec_id] = sec
            for ssec in sec.get("sub_sections", []):
                ssec_id = ssec.get("id")
                if ssec_id:
                    sub_sections[ssec_id] = (ssec, sec_id)
                    for q in ssec.get("questions", []):
                        q_id = q.get("id")
                        if q_id:
                            questions[q_id] = (q, ssec_id, sec_id)
                            
    return sections, sub_sections, questions

def has_section_changed(sec1, sec2):
    if not sec1 or not sec2:
        return True
    fields = ["title", "description", "repeatable", "min_repeats", "max_repeats", "visibility_rules"]
    for f in fields:
        if sec1.get(f) != sec2.get(f):
            return True
    return False

def has_subsection_changed(ssec1, ssec2):
    if not ssec1 or not ssec2:
        return True
    fields = ["title", "repeatable", "max_repeats", "visibility_rules"]
    for f in fields:
        if ssec1.get(f) != ssec2.get(f):
            return True
    return False

def three_way_merge(form_id, source_branch, target_branch, author_id):
    fid = ObjectId(form_id) if isinstance(form_id, str) and ObjectId.is_valid(form_id) else form_id
    
    # Retrieve form
    form = mongo.db.forms.find_one({"_id": fid, "is_deleted": False})
    if not form:
        raise ValueError(f"Form {form_id} not found")

    branches = form.get("branches", {})
    if source_branch not in branches:
        raise ValueError(f"Source branch {source_branch} not found")
    if target_branch not in branches:
        raise ValueError(f"Target branch {target_branch} not found")
        
    source_commit_id = branches[source_branch]
    target_commit_id = branches[target_branch]
    
    if source_commit_id == target_commit_id:
        # Already fully merged
        return {"status": "merged", "commit_id": target_commit_id}
        
    # Find common ancestor
    base_commit_id = find_common_ancestor(fid, target_commit_id, source_commit_id)
    if not base_commit_id:
        raise ValueError("No common ancestor found between branches")
        
    # Retrieve commits
    commit_base = mongo.db.form_commits.find_one({"form_id": fid, "commit_id": base_commit_id})
    commit_A = mongo.db.form_commits.find_one({"form_id": fid, "commit_id": target_commit_id})
    commit_B = mongo.db.form_commits.find_one({"form_id": fid, "commit_id": source_commit_id})
    
    if not commit_base or not commit_A or not commit_B:
        raise ValueError("Failed to retrieve branch or base commits")
        
    schema_base = commit_base.get("schema", {})
    schema_A = commit_A.get("schema", {})
    schema_B = commit_B.get("schema", {})
    
    # Index elements
    sections_base, sub_sections_base, questions_base = index_schema_elements(schema_base)
    sections_A, sub_sections_A, questions_A = index_schema_elements(schema_A)
    sections_B, sub_sections_B, questions_B = index_schema_elements(schema_B)
    
    # All element IDs
    all_sec_ids = set(sections_base.keys()) | set(sections_A.keys()) | set(sections_B.keys())
    all_ssec_ids = set(sub_sections_base.keys()) | set(sub_sections_A.keys()) | set(sub_sections_B.keys())
    all_q_ids = set(questions_base.keys()) | set(questions_A.keys()) | set(questions_B.keys())
    
    conflict_fields = []
    
    # 1. Form-level check: ui, access, settings
    for key in ["ui", "access", "settings"]:
        val_base = schema_base.get(key)
        val_A = schema_A.get(key)
        val_B = schema_B.get(key)
        
        changed_A = (val_A != val_base)
        changed_B = (val_B != val_base)
        
        if changed_A and changed_B and (val_A != val_B):
            conflict_fields.append(key)
            
    # 2. Section check
    for sec_id in all_sec_ids:
        sec_base = sections_base.get(sec_id)
        sec_A = sections_A.get(sec_id)
        sec_B = sections_B.get(sec_id)
        
        changed_A = has_section_changed(sec_base, sec_A)
        changed_B = has_section_changed(sec_base, sec_B)
        
        if changed_A and changed_B:
            # If deleted in one, and modified in other
            if not sec_A and sec_B:
                conflict_fields.append(f"sections.{sec_id}")
            elif not sec_B and sec_A:
                conflict_fields.append(f"sections.{sec_id}")
            elif sec_A and sec_B:
                for f in ["title", "description", "repeatable", "min_repeats", "max_repeats", "visibility_rules"]:
                    val_base = sec_base.get(f) if sec_base else None
                    val_A = sec_A.get(f)
                    val_B = sec_B.get(f)
                    if (val_A != val_base) and (val_B != val_base) and (val_A != val_B):
                        conflict_fields.append(f"sections.{sec_id}.{f}")
                        
    # 3. Sub-section check
    for ssec_id in all_ssec_ids:
        ssec_base_info = sub_sections_base.get(ssec_id)
        ssec_A_info = sub_sections_A.get(ssec_id)
        ssec_B_info = sub_sections_B.get(ssec_id)
        
        ssec_base = ssec_base_info[0] if ssec_base_info else None
        ssec_A = ssec_A_info[0] if ssec_A_info else None
        ssec_B = ssec_B_info[0] if ssec_B_info else None
        
        parent_sec_id = None
        if ssec_A_info:
            parent_sec_id = ssec_A_info[1]
        elif ssec_B_info:
            parent_sec_id = ssec_B_info[1]
        elif ssec_base_info:
            parent_sec_id = ssec_base_info[1]
            
        changed_A = has_subsection_changed(ssec_base, ssec_A)
        changed_B = has_subsection_changed(ssec_base, ssec_B)
        
        if changed_A and changed_B:
            if not ssec_A and ssec_B:
                conflict_fields.append(f"sections.{parent_sec_id}.sub_sections.{ssec_id}")
            elif not ssec_B and ssec_A:
                conflict_fields.append(f"sections.{parent_sec_id}.sub_sections.{ssec_id}")
            elif ssec_A and ssec_B:
                for f in ["title", "repeatable", "max_repeats", "visibility_rules"]:
                    val_base = ssec_base.get(f) if ssec_base else None
                    val_A = ssec_A.get(f)
                    val_B = ssec_B.get(f)
                    if (val_A != val_base) and (val_B != val_base) and (val_A != val_B):
                        conflict_fields.append(f"sections.{parent_sec_id}.sub_sections.{ssec_id}.{f}")
                        
    # 4. Question check
    for q_id in all_q_ids:
        q_base_info = questions_base.get(q_id)
        q_A_info = questions_A.get(q_id)
        q_B_info = questions_B.get(q_id)
        
        q_base = q_base_info[0] if q_base_info else None
        q_A = q_A_info[0] if q_A_info else None
        q_B = q_B_info[0] if q_B_info else None
        
        parent_ssec_id = None
        parent_sec_id = None
        if q_A_info:
            parent_ssec_id = q_A_info[1]
            parent_sec_id = q_A_info[2]
        elif q_B_info:
            parent_ssec_id = q_B_info[1]
            parent_sec_id = q_B_info[2]
        elif q_base_info:
            parent_ssec_id = q_base_info[1]
            parent_sec_id = q_base_info[2]
            
        changed_A = (q_A != q_base)
        changed_B = (q_B != q_base)
        
        if changed_A and changed_B and (q_A != q_B):
            if not q_A and q_B:
                conflict_fields.append(f"sections.{parent_sec_id}.sub_sections.{parent_ssec_id}.questions.{q_id}")
            elif not q_B and q_A:
                conflict_fields.append(f"sections.{parent_sec_id}.sub_sections.{parent_ssec_id}.questions.{q_id}")
            elif q_A and q_B:
                q_fields = ["type", "label", "description", "required", "properties", "visibility_rules", 
                            "validation_rules", "calculations", "fetch_action", "skip_logic", "ui"]
                for f in q_fields:
                    val_base = q_base.get(f) if q_base else None
                    val_A = q_A.get(f)
                    val_B = q_B.get(f)
                    if (val_A != val_base) and (val_B != val_base) and (val_A != val_B):
                        conflict_fields.append(f"sections.{parent_sec_id}.sub_sections.{parent_ssec_id}.questions.{q_id}.{f}")
                        
    # Populate our_changes
    our_changes = {}
    if schema_A.get("ui") != schema_base.get("ui"):
        our_changes["ui"] = schema_A.get("ui")
    if schema_A.get("access") != schema_base.get("access"):
        our_changes["access"] = schema_A.get("access")
    if schema_A.get("settings") != schema_base.get("settings"):
        our_changes["settings"] = schema_A.get("settings")
        
    sec_changes = {}
    for sec_id, sec_A in sections_A.items():
        sec_base = sections_base.get(sec_id)
        if not sec_base or has_section_changed(sec_base, sec_A):
            sec_changes[sec_id] = sec_A
    for sec_id in sections_base:
        if sec_id not in sections_A:
            sec_changes[sec_id] = {"deleted": True}
    if sec_changes:
        our_changes["sections"] = sec_changes

    if conflict_fields:
        # Create pending merge record
        pending_merge_doc = {
            "form_id": fid,
            "branch_name": target_branch,
            "base_commit_id": base_commit_id,
            "their_commit_id": source_commit_id,
            "our_changes": our_changes,
            "conflict_fields": conflict_fields,
            "status": "pending",
            "resolver_id": None,
            "resolved_at": None,
            "created_at": datetime.datetime.utcnow().isoformat(),
            "created_by": ObjectId(author_id) if isinstance(author_id, str) and ObjectId.is_valid(author_id) else author_id
        }
        res = mongo.db.pending_merges.insert_one(pending_merge_doc)
        return {
            "status": "conflict",
            "pending_merge_id": str(res.inserted_id),
            "conflict_fields": conflict_fields
        }
        
    # Auto-merge!
    # Construct a merged schema starting with base
    merged_schema = {}
    
    # 1. Merge form-level key-values
    for key in ["ui", "access", "settings", "webhook_configs"]:
        val_base = schema_base.get(key) if schema_base else None
        val_A = schema_A.get(key)
        val_B = schema_B.get(key)
        
        if val_A != val_base:
            merged_schema[key] = val_A
        elif val_B != val_base:
            merged_schema[key] = val_B
        else:
            merged_schema[key] = val_base
            
    # 2. Merge sections, sub-sections, and questions
    merged_sections = []
    
    for sec_id, sec_A in sections_A.items():
        sec_base = sections_base.get(sec_id)
        sec_B = sections_B.get(sec_id)
        
        if not sec_base:
            # Added in A
            merged_sections.append(sec_A)
        else:
            # Was in base
            if not sec_B:
                # Deleted in B
                if has_section_changed(sec_base, sec_A):
                    # Modified in A, deleted in B
                    merged_sections.append(sec_A)
                else:
                    # Deleted in merge
                    continue
            else:
                # Exists in A and B
                m_sec = dict(sec_A if has_section_changed(sec_base, sec_A) else sec_B)
                
                # Merge sub-sections
                m_ssecs = []
                ssecs_A = {s["id"]: s for s in sec_A.get("sub_sections", [])}
                ssecs_B = {s["id"]: s for s in sec_B.get("sub_sections", [])}
                ssecs_base = {s["id"]: s for s in sec_base.get("sub_sections", [])}
                
                for ssec_id, ssec_A in ssecs_A.items():
                    ssec_base = ssecs_base.get(ssec_id)
                    ssec_B = ssecs_B.get(ssec_id)
                    
                    if not ssec_base:
                        m_ssecs.append(ssec_A)
                    else:
                        if not ssec_B:
                            if has_subsection_changed(ssec_base, ssec_A):
                                m_ssecs.append(ssec_A)
                            else:
                                continue
                        else:
                            m_ssec = dict(ssec_A if has_subsection_changed(ssec_base, ssec_A) else ssec_B)
                            
                            # Merge questions
                            m_qs = []
                            qs_A = {q["id"]: q for q in ssec_A.get("questions", [])}
                            qs_B = {q["id"]: q for q in ssec_B.get("questions", [])}
                            qs_base = {q["id"]: q for q in ssec_base.get("questions", [])}
                            
                            for q_id, q_A in qs_A.items():
                                q_base = qs_base.get(q_id)
                                q_B = qs_B.get(q_id)
                                
                                if not q_base:
                                    m_qs.append(q_A)
                                else:
                                    if not q_B:
                                        if q_A != q_base:
                                            m_qs.append(q_A)
                                        else:
                                            continue
                                    else:
                                        m_qs.append(q_A if q_A != q_base else q_B)
                                        
                            for q_id, q_B in qs_B.items():
                                if q_id not in qs_A and q_id not in qs_base:
                                    m_qs.append(q_B)
                                    
                            m_ssec["questions"] = m_qs
                            m_ssecs.append(m_ssec)
                            
                for ssec_id, ssec_B in ssecs_B.items():
                    if ssec_id not in ssecs_A and ssec_id not in ssecs_base:
                        m_ssecs.append(ssec_B)
                        
                m_sec["sub_sections"] = m_ssecs
                merged_sections.append(m_sec)
                
    for sec_id, sec_B in sections_B.items():
        if sec_id not in sections_A and sec_id not in sections_base:
            merged_sections.append(sec_B)
            
    merged_schema["sections"] = merged_sections
    
    # Create the merge commit
    message = f"Merge branch {source_branch} into {target_branch}"
    new_commit = create_commit(
        form_id=fid,
        schema=merged_schema,
        author_id=author_id,
        message=message,
        branch=target_branch,
        parent_ids=[target_commit_id, source_commit_id]
    )
    
    return {"status": "merged", "commit_id": new_commit["commit_id"]}


def delete_branch(form_id, branch_name):
    """Delete a branch from a form."""
    fid = ObjectId(form_id) if isinstance(form_id, str) and ObjectId.is_valid(form_id) else form_id
    
    form = mongo.db.forms.find_one({"_id": fid, "is_deleted": False})
    if not form:
        raise ValueError(f"Form {form_id} not found")
        
    branches = form.get("branches", {})
    if branch_name not in branches:
        raise ValueError(f"Branch {branch_name} not found for form {form_id}")
        
    if branch_name == "main":
        raise ValueError("Cannot delete the main branch")
        
    if branch_name == form.get("production_branch"):
        raise ValueError("Cannot delete the production branch")
        
    # Remove the branch
    mongo.db.forms.update_one(
        {"_id": fid, "is_deleted": False},
        {
            "$unset": {f"branches.{branch_name}": ""},
            "$set": {"updated_at": datetime.datetime.utcnow().isoformat()}
        }
    )
    
    return {"status": "deleted", "branch": branch_name}


def list_branches(form_id):
    """List all branches for a form."""
    fid = ObjectId(form_id) if isinstance(form_id, str) and ObjectId.is_valid(form_id) else form_id
    
    form = mongo.db.forms.find_one({"_id": fid, "is_deleted": False})
    if not form:
        raise ValueError(f"Form {form_id} not found")
        
    branches = form.get("branches", {})
    production_branch = form.get("production_branch", "main")
    
    result = []
    for branch_name, commit_id in branches.items():
        commit = mongo.db.form_commits.find_one(
            {"form_id": fid, "commit_id": commit_id}
        )
        result.append({
            "name": branch_name,
            "commit_id": commit_id,
            "is_production": branch_name == production_branch,
            "created_at": commit.get("timestamp") if commit else None,
            "author_id": commit.get("author_id") if commit else None
        })
        
    return result


def create_tag(form_id, tag_name, commit_id, message=None):
    """Create a tag for a specific commit."""
    fid = ObjectId(form_id) if isinstance(form_id, str) and ObjectId.is_valid(form_id) else form_id
    
    # Verify form exists
    form = mongo.db.forms.find_one({"_id": fid, "is_deleted": False})
    if not form:
        raise ValueError(f"Form {form_id} not found")
        
    # Verify commit exists
    commit = mongo.db.form_commits.find_one({"form_id": fid, "commit_id": commit_id})
    if not commit:
        raise ValueError(f"Commit {commit_id} not found for form {form_id}")
        
    # Check if tag already exists
    tags = form.get("tags", {})
    if tag_name in tags:
        raise ValueError(f"Tag {tag_name} already exists for form {form_id}")
        
    # Update the commit with tag information
    mongo.db.form_commits.update_one(
        {"form_id": fid, "commit_id": commit_id},
        {
            "$set": {
                "tag": tag_name,
                "updated_at": datetime.datetime.utcnow().isoformat()
            }
        }
    )
    
    # Update form's tags
    mongo.db.forms.update_one(
        {"_id": fid, "is_deleted": False},
        {
            "$set": {
                f"tags.{tag_name}": commit_id,
                "updated_at": datetime.datetime.utcnow().isoformat()
            }
        }
    )
    
    return {
        "tag": tag_name,
        "commit_id": commit_id,
        "message": message or f"Tag {tag_name} created",
        "created_at": datetime.datetime.utcnow().isoformat()
    }


def delete_tag(form_id, tag_name):
    """Delete a tag from a form."""
    fid = ObjectId(form_id) if isinstance(form_id, str) and ObjectId.is_valid(form_id) else form_id
    
    form = mongo.db.forms.find_one({"_id": fid, "is_deleted": False})
    if not form:
        raise ValueError(f"Form {form_id} not found")
        
    tags = form.get("tags", {})
    if tag_name not in tags:
        raise ValueError(f"Tag {tag_name} not found for form {form_id}")
        
    commit_id = tags[tag_name]
    
    # Remove tag from commit
    mongo.db.form_commits.update_one(
        {"form_id": fid, "commit_id": commit_id},
        {
            "$unset": {"tag": ""},
            "$set": {"updated_at": datetime.datetime.utcnow().isoformat()}
        }
    )
    
    # Remove tag from form
    mongo.db.forms.update_one(
        {"_id": fid, "is_deleted": False},
        {
            "$unset": {f"tags.{tag_name}": ""},
            "$set": {"updated_at": datetime.datetime.utcnow().isoformat()}
        }
    )
    
    return {"status": "deleted", "tag": tag_name}


def list_tags(form_id):
    """List all tags for a form."""
    fid = ObjectId(form_id) if isinstance(form_id, str) and ObjectId.is_valid(form_id) else form_id
    
    form = mongo.db.forms.find_one({"_id": fid, "is_deleted": False})
    if not form:
        raise ValueError(f"Form {form_id} not found")
        
    tags = form.get("tags", {})
    
    result = []
    for tag_name, commit_id in tags.items():
        commit = mongo.db.form_commits.find_one(
            {"form_id": fid, "commit_id": commit_id}
        )
        result.append({
            "name": tag_name,
            "commit_id": commit_id,
            "created_at": commit.get("timestamp") if commit else None,
            "author_id": commit.get("author_id") if commit else None,
            "message": commit.get("message") if commit else None
        })
        
    return result


def publish_branch(form_id, branch_name, author_id, message=None):
    """Publish a branch to production."""
    fid = ObjectId(form_id) if isinstance(form_id, str) and ObjectId.is_valid(form_id) else form_id
    uid = ObjectId(author_id) if isinstance(author_id, str) and ObjectId.is_valid(author_id) else author_id
    
    form = mongo.db.forms.find_one({"_id": fid, "is_deleted": False})
    if not form:
        raise ValueError(f"Form {form_id} not found")
        
    branches = form.get("branches", {})
    if branch_name not in branches:
        raise ValueError(f"Branch {branch_name} not found for form {form_id}")
        
    commit_id = branches[branch_name]
    
    # Create a new commit for the publication
    publish_message = message or f"Publish branch {branch_name} to production"
    new_commit = create_commit(
        form_id=fid,
        schema=mongo.db.form_commits.find_one({"form_id": fid, "commit_id": commit_id})["schema"],
        author_id=uid,
        message=publish_message,
        branch=branch_name,
        parent_ids=[commit_id]
    )
    
    # Update production branch
    mongo.db.forms.update_one(
        {"_id": fid, "is_deleted": False},
        {
            "$set": {
                "production_branch": branch_name,
                f"branches.{branch_name}": new_commit["commit_id"],
                "updated_at": datetime.datetime.utcnow().isoformat()
            }
        }
    )
    
    return {
        "status": "published",
        "production_branch": branch_name,
        "commit_id": new_commit["commit_id"],
        "message": publish_message
    }


def get_commit_history(form_id, branch_name=None, limit=50, skip=0):
    """Get commit history for a form or branch."""
    fid = ObjectId(form_id) if isinstance(form_id, str) and ObjectId.is_valid(form_id) else form_id
    
    form = mongo.db.forms.find_one({"_id": fid, "is_deleted": False})
    if not form:
        raise ValueError(f"Form {form_id} not found")
        
    query = {"form_id": fid}
    if branch_name:
        query["branch"] = branch_name
        
    commits = list(mongo.db.form_commits.find(query)
                  .sort("timestamp", -1)
                  .skip(skip)
                  .limit(limit))
    
    result = []
    for commit in commits:
        result.append({
            "commit_id": commit["commit_id"],
            "message": commit["message"],
            "author_id": str(commit["author_id"]),
            "branch": commit["branch"],
            "tag": commit.get("tag"),
            "timestamp": commit["timestamp"],
            "parent_ids": commit["parent_ids"]
        })
        
    return result


def get_commit_diff(form_id, commit_a_id, commit_b_id):
    """Get the differences between two commits."""
    fid = ObjectId(form_id) if isinstance(form_id, str) and ObjectId.is_valid(form_id) else form_id
    
    commit_a = mongo.db.form_commits.find_one({"form_id": fid, "commit_id": commit_a_id})
    commit_b = mongo.db.form_commits.find_one({"form_id": fid, "commit_id": commit_b_id})
    
    if not commit_a or not commit_b:
        raise ValueError("One or both commits not found")
        
    schema_a = commit_a.get("schema", {})
    schema_b = commit_b.get("schema", {})
    
    diff = {
        "additions": {},
        "deletions": {},
        "modifications": {},
        "conflicts": []
    }
    
    # Compare form-level fields
    for key in ["ui", "access", "settings"]:
        if key in schema_b and key not in schema_a:
            diff["additions"][key] = schema_b[key]
        elif key in schema_a and key not in schema_b:
            diff["deletions"][key] = schema_a[key]
        elif key in schema_a and key in schema_b and schema_a[key] != schema_b[key]:
            diff["modifications"][key] = {
                "from": schema_a[key],
                "to": schema_b[key]
            }
    
    # Compare sections (simplified - could be enhanced for detailed section comparison)
    sections_a = {s["id"]: s for s in schema_a.get("sections", [])}
    sections_b = {s["id"]: s for s in schema_b.get("sections", [])}
    
    for sec_id, sec_b in sections_b.items():
        if sec_id not in sections_a:
            diff["additions"][f"sections.{sec_id}"] = sec_b
        elif sections_a[sec_id] != sec_b:
            diff["modifications"][f"sections.{sec_id}"] = {
                "from": sections_a[sec_id],
                "to": sec_b
            }
    
    for sec_id, sec_a in sections_a.items():
        if sec_id not in sections_b:
            diff["deletions"][f"sections.{sec_id}"] = sec_a
    
    return diff


def resolve_merge_conflict(form_id, pending_merge_id, resolved_fields, resolver_id):
    """Resolve a merge conflict."""
    fid = ObjectId(form_id) if isinstance(form_id, str) and ObjectId.is_valid(form_id) else form_id
    pmid = ObjectId(pending_merge_id) if isinstance(pending_merge_id, str) and ObjectId.is_valid(pending_merge_id) else pending_merge_id
    rid = ObjectId(resolver_id) if isinstance(resolver_id, str) and ObjectId.is_valid(resolver_id) else resolver_id
    
    # Get the pending merge record
    pending_merge = mongo.db.pending_merges.find_one({"_id": pmid, "form_id": fid})
    if not pending_merge:
        raise ValueError(f"Pending merge {pending_merge_id} not found")
        
    if pending_merge.get("status") != "pending":
        raise ValueError(f"Merge {pending_merge_id} is not in pending status")
    
    # Get the commits involved
    base_commit_id = pending_merge["base_commit_id"]
    their_commit_id = pending_merge["their_commit_id"]
    
    commit_base = mongo.db.form_commits.find_one({"form_id": fid, "commit_id": base_commit_id})
    commit_their = mongo.db.form_commits.find_one({"form_id": fid, "commit_id": their_commit_id})
    
    if not commit_base or not commit_their:
        raise ValueError("Failed to retrieve base or their commit")
    
    # Start with their schema and apply resolved fields
    merged_schema = dict(commit_their["schema"])
    
    # Apply resolved fields
    for field_path, resolved_value in resolved_fields.items():
        # Simple field path resolution (could be enhanced for nested paths)
        if "." in field_path:
            parts = field_path.split(".")
            current = merged_schema
            for part in parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]
            current[parts[-1]] = resolved_value
        else:
            merged_schema[field_path] = resolved_value
    
    # Get the target branch
    form = mongo.db.forms.find_one({"_id": fid, "is_deleted": False})
    target_branch = pending_merge["branch_name"]
    target_commit_id = form["branches"][target_branch]
    
    # Create the merge commit
    message = f"Resolve merge conflict for branch {target_branch}"
    new_commit = create_commit(
        form_id=fid,
        schema=merged_schema,
        author_id=rid,
        message=message,
        branch=target_branch,
        parent_ids=[target_commit_id, their_commit_id]
    )
    
    # Update pending merge status
    mongo.db.pending_merges.update_one(
        {"_id": pmid},
        {
            "$set": {
                "status": "resolved",
                "resolver_id": rid,
                "resolved_at": datetime.datetime.utcnow().isoformat()
            }
        }
    )
    
    return {
        "status": "resolved",
        "commit_id": new_commit["commit_id"],
        "message": message
    }


def get_pending_merges(form_id):
    """Get all pending merges for a form."""
    fid = ObjectId(form_id) if isinstance(form_id, str) and ObjectId.is_valid(form_id) else form_id
    
    pending_merges = list(mongo.db.pending_merges.find({
        "form_id": fid,
        "status": "pending"
    }))
    
    result = []
    for pm in pending_merges:
        result.append({
            "id": str(pm["_id"]),
            "branch_name": pm["branch_name"],
            "base_commit_id": pm["base_commit_id"],
            "their_commit_id": pm["their_commit_id"],
            "conflict_fields": pm["conflict_fields"],
            "created_at": pm["created_at"],
            "created_by": str(pm["created_by"])
        })
        
    return result


def abandon_merge_conflict(form_id, pending_merge_id, user_id):
    """Abandon a pending merge conflict."""
    fid = ObjectId(form_id) if isinstance(form_id, str) and ObjectId.is_valid(form_id) else form_id
    pmid = ObjectId(pending_merge_id) if isinstance(pending_merge_id, str) and ObjectId.is_valid(pending_merge_id) else pending_merge_id
    uid = ObjectId(user_id) if isinstance(user_id, str) and ObjectId.is_valid(user_id) else user_id
    
    pending_merge = mongo.db.pending_merges.find_one({"_id": pmid, "form_id": fid})
    if not pending_merge:
        raise ValueError(f"Pending merge {pending_merge_id} not found")
        
    if pending_merge.get("status") != "pending":
        raise ValueError(f"Merge {pending_merge_id} is not in pending status")
    
    # Only the creator or admin can abandon
    if pending_merge["created_by"] != uid:
        # Check if user is admin (simplified - should use proper auth service)
        user = mongo.db.users.find_one({"_id": uid})
        if not user or user.get("system_role") != "super_admin":
            raise ValueError("Only the merge creator or admin can abandon the merge")
    
    # Update pending merge status
    mongo.db.pending_merges.update_one(
        {"_id": pmid},
        {
            "$set": {
                "status": "abandoned",
                "resolved_at": datetime.datetime.utcnow().isoformat()
            }
        }
    )
    
    return {"status": "abandoned", "pending_merge_id": str(pmid)}
