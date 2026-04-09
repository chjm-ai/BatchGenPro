# Seedance Video Models Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace Seedance 1.5 with Seedance 2.0 and 2.0 fast, and align Doubao video generation with the current Ark API.

**Architecture:** Keep the existing video generation flow intact. Update the backend Doubao adapter to use the latest Ark task endpoints and update the frontend video model selection and API configuration checks so they follow the selected model instead of hard-coded `sora`.

**Tech Stack:** Flask, Python stdlib `unittest`, Vue 3, Element Plus

---

### Task 1: Lock backend Doubao API behavior with tests

**Files:**
- Create: `backend/tests/test_video_generator.py`
- Modify: `backend/video_generator.py`

- [ ] Step 1: Write failing tests for Doubao task endpoints and default model.
- [ ] Step 2: Run `python3 -m unittest backend.tests.test_video_generator -v` and confirm failure.
- [ ] Step 3: Update `DoubaoVideoGenerator` to use the official task endpoints and new default model.
- [ ] Step 4: Run `python3 -m unittest backend.tests.test_video_generator -v` and confirm pass.

### Task 2: Update frontend video model options and API-type checks

**Files:**
- Modify: `frontend/src/App.vue`
- Modify: `frontend/src/utils/apiConfig.js`

- [ ] Step 1: Remove Seedance 1.5 Pro and add Seedance 2.0 / 2.0 fast to the video model list.
- [ ] Step 2: Make video model change handling and submit validation use the selected model’s `apiType`.
- [ ] Step 3: Keep Sora behavior unchanged.

### Task 3: Verify integration surfaces

**Files:**
- Modify: `frontend/src/App.vue`
- Modify: `backend/video_generator.py`

- [ ] Step 1: Re-read touched code for regressions.
- [ ] Step 2: Run `python3 -m unittest backend.tests.test_video_generator -v`.
- [ ] Step 3: Run `npm run build` in `frontend` if dependencies are available.
