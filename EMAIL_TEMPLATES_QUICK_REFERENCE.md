# Quick Reference: Email Templates

## Import Statement
```python
from core.email_templates import EmailTemplates, format_datetime_for_email
```

## Common Usage Patterns

### 1. Client Onboarding (Lawyer invites Client)
```python
subject, body = EmailTemplates.client_signup_invitation(
    client_fname="John",
    lawyer_fname="Sarah",
    lawyer_lname="Smith",
    signup_link="https://mamla.ai/signup?token=..."
)
send_email_celery.delay(client_email, subject, body)
```

### 2. Welcome Email (After Verification)
```python
subject, body = EmailTemplates.welcome_email(
    fname="John",
    user_id="john_20240101123456"
)
send_email_celery.delay(user_email, subject, body)
```

### 3. Event Creation (With Participants)
```python
formatted_start = format_datetime_for_email(start_datetime)
formatted_end = format_datetime_for_email(end_datetime)

subject, body = EmailTemplates.event_created_with_party(
    fname="John",
    lname="Doe",
    start_datetime=formatted_start,
    end_datetime=formatted_end,
    meet_link="https://meet.example.com/xyz"
)
send_email_celery.delay(user_email, subject, body)
```

### 4. Event Creation (Personal Task)
```python
subject, body = EmailTemplates.event_created_solo(
    fname="John",
    lname="Doe",
    start_datetime=formatted_start,
    end_datetime=formatted_end,
    meet_link=None  # Optional
)
send_email_celery.delay(user_email, subject, body)
```

### 5. Event Update (Entire Series)
```python
import json
updated_fields_json = json.dumps({
    "START_TIME": "10:00 AM",
    "END_TIME": "11:00 AM",
    "LOCATION": "Conference Room B"
}, indent=4)

subject, body = EmailTemplates.event_updated_entire_series(
    fname="John",
    lname="Doe",
    title="Weekly Team Meeting",
    updated_fields=updated_fields_json
)
send_email_celery.delay(user_email, subject, body)
```

### 6. Event Update (Single Event)
```python
subject, body = EmailTemplates.event_updated_single(
    fname="John",
    lname="Doe",
    title="Client Meeting",
    updated_fields=updated_fields_json
)
send_email_celery.delay(user_email, subject, body)
```

### 7. Event Deletion (Series)
```python
subject, body = EmailTemplates.event_deleted_series(
    fname="John",
    lname="Doe",
    title="Weekly Team Meeting"
)
send_email_celery.delay(user_email, subject, body)
```

### 8. Event Deletion (Single)
```python
subject, body = EmailTemplates.event_deleted_single(
    fname="John",
    lname="Doe",
    title="Client Meeting"
)
send_email_celery.delay(user_email, subject, body)
```

### 9. Meeting Reminder
```python
subject, body = EmailTemplates.event_reminder(
    fname="John",
    lname="Doe",
    title="Client Meeting",
    start_time="Today at 3:00 PM",
    meet_link="https://meet.example.com/xyz"
)
send_email_celery.delay(user_email, subject, body)
```

### 10. Draft Ready Notification
```python
subject, body = EmailTemplates.draft_ready(
    fname="John",
    lname="Doe",
    draft_title="Contract Agreement - ABC Corp"
)
send_email_celery.delay(user_email, subject, body)
```

## Date Formatting Helper

```python
# Input formats
datetime_with_time = "2024-09-17T22:01"    # With time
date_only = "2024-09-17"                    # Date only

# Format for email display
formatted_datetime = format_datetime_for_email(datetime_with_time)
# Output: "September 17, 2024 at 10:01 PM"

formatted_date = format_datetime_for_email(date_only)
# Output: "September 17, 2024"

# Use in email
subject, body = EmailTemplates.event_created_solo(
    fname="John",
    lname="Doe",
    start_datetime=format_datetime_for_email(start),
    end_datetime=format_datetime_for_email(end),
    meet_link=None
)
```

## Updating Branding

All emails automatically use these values from `EmailTemplates`:

```python
COMPANY_NAME = "Mamla.ai"
SUPPORT_EMAIL = "support@mamla.ai"
WEBSITE_URL = "https://mamla.ai"
```

To change branding, update these constants in `Legalv1/core/email_templates.py`.

## Template Structure

All templates follow this pattern:

```python
@classmethod
def template_name(cls, param1, param2):
    """When this email is sent"""
    subject = "Email Subject"
    body = f"""Dear {param1},

Email content here...

{cls.get_footer()}"""
    return subject, body
```

## Return Value

All template methods return: `(subject: str, body: str)`

```python
subject, body = EmailTemplates.some_template(...)
# subject = "Email Subject"
# body = "Full email body with footer"
```

## With CC Emails (Calendar Events)

```python
# For calendar events with multiple participants
subject, body = EmailTemplates.event_created_with_party(...)
send_email_celery.delay(
    user_email,      # Primary recipient
    subject,
    body,
    cc_emails        # CC to other participants
)
```

## Error Handling

```python
try:
    subject, body = EmailTemplates.welcome_email(fname, user_id)
    send_email_celery.delay(email, subject, body)
except Exception as e:
    logger.error(f"Failed to send welcome email: {e}")
```

## Best Practices

1. **Always format datetimes** before passing to templates
2. **Provide all required parameters** - templates don't have defaults
3. **Use descriptive variable names** when extracting subject/body
4. **Log email sends** for debugging
5. **Handle None/optional parameters** (e.g., meet_link)

## Available Templates

| Template | Use Case | Required Params |
|----------|----------|-----------------|
| `welcome_email` | Account verified | fname, user_id |
| `client_signup_invitation` | Lawyer invites client | client_fname, lawyer_fname, lawyer_lname, signup_link |
| `event_created_with_party` | Meeting with others | fname, lname, start_datetime, end_datetime, meet_link? |
| `event_created_solo` | Personal task | fname, lname, start_datetime, end_datetime, meet_link? |
| `event_updated_entire_series` | Series updated | fname, lname, title, updated_fields |
| `event_updated_single` | Event updated | fname, lname, title, updated_fields |
| `event_deleted_series` | Series cancelled | fname, lname, title |
| `event_deleted_single` | Event cancelled | fname, lname, title |
| `event_reminder` | Meeting reminder | fname, lname, title, start_time, meet_link? |
| `draft_ready` | Document ready | fname, lname, draft_title |
| `session_notification` | New login | fname, lname, device_type, location, ip_address |
| `feedback_acknowledgment` | Feedback received | fname |

---

**For full documentation:** See `Legalv1/core/EMAIL_TEMPLATES_README.md`
