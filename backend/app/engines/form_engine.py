import hashlib
import datetime
from bson import ObjectId
from app.extensions import mongo

def generate_commit_id(form_id, timestamp, author_id):
    raw_str = f"{str(form_id)}{str(timestamp)}{str(author_id)}"
    return hashlib.sha256(raw_str.encode("utf-8")).hexdigest()[:12]

def create_commit(form_id, schema, author_id, message, branch, parent_ids=[]):
    timestamp = datetime.datetime.utcnow().isoformat()
    commit_id = generate_commit_id(form_id, timestamp, author_id)
    
    fid = ObjectId(form_id) if isinstance(form_id, str) and ObjectId.is_valid(form_id) else form_id
    uid = ObjectId(author_id) if isinstance(author_id, str) and ObjectId.is_valid(author_id) else author_id
    
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
        {"_id": fid},
        {
            "$set": {
                f"branches.{branch}": commit_id,
                "updated_at": timestamp
            }
        },
        upsert=True
    )
    
    return commit_doc

def create_branch(form_id, name, from_commit_id):
    fid = ObjectId(form_id) if isinstance(form_id, str) and ObjectId.is_valid(form_id) else form_id
    
    # Check if branch already exists in form
    form = mongo.db.forms.find_one({"_id": fid})
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
        {"_id": fid},
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
    form = mongo.db.forms.find_one({"_id": fid})
    if not form:
        raise ValueError(f"Form {form_id} not found")
        
    if "branches" not in form or source_branch not in form["branches"]:
        raise ValueError(f"Source branch {source_branch} not found")
    if target_branch not in form["branches"]:
        raise ValueError(f"Target branch {target_branch} not found")
        
    source_commit_id = form["branches"][source_branch]
    target_commit_id = form["branches"][target_branch]
    
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
