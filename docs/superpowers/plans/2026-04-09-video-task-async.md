# Video Task Async Implementation Plan

**Goal:** Make `/api/batch/generate-video` return immediately after task creation and move video generation to background execution.

**Architecture:** Keep the existing Redis task model and synchronous processing function, but invoke that function from a background daemon thread so the HTTP request is no longer tied to provider latency.

**Tech Stack:** Flask, Python stdlib `threading`, Python stdlib `unittest`, Vue 3

### Task 1: Lock async submit behavior with a failing test

**Files:**
- Modify: `backend/tests/test_video_generator.py`

- [ ] Add a route-level test that expects `/api/batch/generate-video` to schedule a background task and return `task_id` immediately.
- [ ] Run `python3 -m unittest backend.tests.test_video_generator -v` and confirm the new test fails first.

### Task 2: Implement background scheduling in the backend

**Files:**
- Modify: `backend/app.py`

- [ ] Add a helper that starts background video processing in a daemon thread.
- [ ] Update the route so it starts the background thread and returns without waiting for provider completion.
- [ ] Keep task status transitions correct for both success and failure paths.

### Task 3: Align frontend wording and verify

**Files:**
- Modify: `frontend/src/App.vue`

- [ ] Update the submit success message to reflect async task submission.
- [ ] Run `python3 -m unittest backend.tests.test_video_generator -v`.
- [ ] Run `npm run build` in `frontend`.
