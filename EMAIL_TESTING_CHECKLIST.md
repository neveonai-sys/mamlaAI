# Testing Checklist - Email Refactoring

## Date: February 28, 2026

After deploying the email template changes, please test the following scenarios to ensure all emails are working correctly and displaying professionally.

---

## 1. User Authentication & Onboarding

### Test 1.1: New User Signup (Standard Flow)
- [ ] Register a new user (Lawyer/Client/Paralegal)
- [ ] Verify email verification link is sent
- [ ] Click verification link
- [ ] **Check:** Welcome email arrives with professional formatting
- [ ] **Verify:** Email contains User ID
- [ ] **Verify:** Email has Mamla.ai branding
- [ ] **Verify:** Support email and website links are present

**Expected Email:** "Welcome to Mamla.ai - Your Account is Active"

---

### Test 1.2: Client Onboarding by Lawyer
- [ ] Login as a Lawyer
- [ ] Navigate to client onboarding
- [ ] Create a new client with email
- [ ] **Check:** Client receives professional signup invitation
- [ ] **Verify:** Email mentions lawyer's name correctly
- [ ] **Verify:** Platform benefits are listed
- [ ] **Verify:** Signup link is present and valid
- [ ] **Verify:** 24-hour expiration notice is mentioned

**Expected Email:** "You've Been Invited to Join Mamla.ai"

---

### Test 1.3: Password Reset (if applicable)
- [ ] Request password reset
- [ ] **Check:** Professional password reset email arrives
- [ ] **Verify:** Reset link works
- [ ] **Verify:** Expiration notice present

**Expected Email:** "Reset Your Password"

---

## 2. Calendar & Meeting Management

### Test 2.1: Create Event with Participants
- [ ] Login as user
- [ ] Create a calendar event with another participant
- [ ] Add meeting link (VideoCall/VoiceCall)
- [ ] **Check:** User receives professional event creation email
- [ ] **Verify:** Dates are formatted nicely (e.g., "September 17, 2024 at 10:01 PM")
- [ ] **Verify:** Meeting link is included
- [ ] **Verify:** Participant email (CC) works correctly

**Expected Email:** "Meeting Scheduled Successfully"

---

### Test 2.2: Create Personal Task/Event
- [ ] Login as user
- [ ] Create a personal task (no participants)
- [ ] **Check:** User receives professional task creation email
- [ ] **Verify:** Proper task details displayed
- [ ] **Verify:** Dates formatted correctly

**Expected Email:** "Task Scheduled Successfully"

---

### Test 2.3: Update Single Event
- [ ] Open an existing event
- [ ] Modify event details (time, location, etc.)
- [ ] Save changes
- [ ] **Check:** Update notification email arrives
- [ ] **Verify:** Updated fields are clearly displayed
- [ ] **Verify:** Professional formatting

**Expected Email:** "Meeting Updated"

---

### Test 2.4: Update Recurring Event Series
- [ ] Create recurring event series
- [ ] Update entire series (all occurrences)
- [ ] **Check:** Series update email arrives
- [ ] **Verify:** Indicates "all events in this series" updated
- [ ] **Verify:** Updated fields displayed

**Expected Email:** "Meeting Series Updated"

---

### Test 2.5: Delete Single Event
- [ ] Delete a single event
- [ ] **Check:** Cancellation email arrives
- [ ] **Verify:** Professional cancellation message
- [ ] **Verify:** Mentions participants were notified

**Expected Email:** "Meeting Cancelled"

---

### Test 2.6: Delete Recurring Event Series
- [ ] Delete entire recurring series
- [ ] **Check:** Series cancellation email arrives
- [ ] **Verify:** Indicates entire series cancelled

**Expected Email:** "Meeting Series Cancelled"

---

## 3. Draft Management

### Test 3.1: Draft Creation with Email
- [ ] Create a legal draft
- [ ] Provide email address for delivery
- [ ] Complete draft creation
- [ ] **Check:** Draft delivery email arrives with attachment
- [ ] **Verify:** PDF is attached correctly
- [ ] **Verify:** Professional message about reviewing draft
- [ ] **Verify:** Instructions to log in for changes

**Expected Email:** "Your Legal Draft is Ready - Mamla.ai"

---

## 4. Email Formatting Verification

### Visual Inspection Checklist
For each email type tested above:

- [ ] **Subject Line:** Professional and descriptive
- [ ] **Salutation:** Uses "Dear {Name}" not "Hi Sir/Mam"
- [ ] **Company Name:** Says "Mamla.ai" not "LegalAI Team"
- [ ] **Body:** Clear, well-structured, professional tone
- [ ] **Bullet Points:** Formatted correctly (where applicable)
- [ ] **Dates/Times:** Human-readable format (not ISO format)
- [ ] **Links:** Working and properly formatted
- [ ] **Footer:** Includes:
  - "Best regards, The Mamla.ai Team"
  - Support email: support@mamla.ai
  - Website: https://mamla.ai
- [ ] **No Typos:** Check for spelling/grammar errors
- [ ] **No Old Branding:** No mentions of "LegalAI Team"

---

## 5. Email Client Compatibility

Test emails render correctly in:

- [ ] Gmail (Web)
- [ ] Gmail (Mobile App)
- [ ] Outlook (Desktop)
- [ ] Outlook (Web)
- [ ] Apple Mail (Mac)
- [ ] Apple Mail (iOS)
- [ ] Yahoo Mail
- [ ] Other email clients used by your users

---

## 6. Edge Cases & Error Handling

### Test 6.1: Missing Data
- [ ] Test with missing names (fname/lname)
- [ ] Verify fallbacks work ("Dear User" instead of crash)

### Test 6.2: Special Characters
- [ ] Test with names containing special characters (é, ñ, etc.)
- [ ] Verify proper encoding

### Test 6.3: Long Content
- [ ] Test with very long event titles
- [ ] Test with many updated fields
- [ ] Verify formatting doesn't break

---

## 7. Functional Tests

### Test 7.1: Email Delivery
- [ ] All test emails actually delivered (not in spam)
- [ ] Delivery time is reasonable (< 1 minute)
- [ ] CC/BCC working for event emails

### Test 7.2: Links & Actions
- [ ] All links in emails are clickable
- [ ] All links navigate to correct pages
- [ ] Signup links work and expire after 24 hours
- [ ] Meeting links are correct

### Test 7.3: Attachments
- [ ] PDF attachments open correctly
- [ ] Attachment file names are appropriate
- [ ] File size is reasonable

---

## 8. Regression Testing

### Verify Old Functionality Still Works
- [ ] User signup flow complete (end-to-end)
- [ ] Login works
- [ ] Password reset works
- [ ] Calendar CRUD operations work
- [ ] Draft creation works
- [ ] Client onboarding works
- [ ] No 500 errors in logs

---

## 9. Performance Tests

- [ ] Email sending doesn't slow down API responses
- [ ] Celery tasks complete successfully
- [ ] No memory leaks from email templates
- [ ] Email queue doesn't get backed up

---

## 10. Security Checks

- [ ] No sensitive data exposed in emails (passwords, tokens, etc.)
- [ ] User IDs are appropriate to share (check with security team)
- [ ] Email links use HTTPS
- [ ] Unsubscribe option present (if required by law)

---

## Issue Tracking

Use this template to report issues:

```
**Issue Type:** [Formatting / Content / Delivery / Link / Other]
**Email Type:** [Welcome / Signup Invitation / Event Created / etc.]
**Description:** [What's wrong]
**Expected:** [What should happen]
**Actual:** [What actually happened]
**Screenshot:** [If applicable]
**Email Client:** [Gmail / Outlook / etc.]
**Priority:** [High / Medium / Low]
```

---

## Sign-Off

Once all tests pass:

- [ ] All email types tested
- [ ] All email clients checked
- [ ] All edge cases verified
- [ ] No critical issues found
- [ ] Documentation updated
- [ ] Team trained on new templates

**Tested By:** ___________________  
**Date:** ___________________  
**Approved By:** ___________________  
**Date:** ___________________  

---

## Rollback Plan

If issues are found after deployment:

1. **Immediate Issues:**
   - Revert to previous commit
   - Redeploy previous version
   - Investigate issue

2. **Minor Issues:**
   - Document the issue
   - Fix in next sprint
   - Monitor user complaints

3. **Major Issues:**
   - Hotfix in separate branch
   - Test thoroughly
   - Deploy ASAP

---

## Post-Deployment Monitoring

For the first week after deployment:

- [ ] Monitor email delivery rates
- [ ] Check for bounce rates increase
- [ ] Review user feedback/complaints
- [ ] Check error logs for email-related errors
- [ ] Verify Celery queue is processing normally
- [ ] Monitor support tickets related to emails

---

**Notes:**

- Keep this checklist updated as new email types are added
- Share results with the team
- Document any deviations from expected behavior
- Update README files if necessary

---

Last Updated: February 28, 2026
