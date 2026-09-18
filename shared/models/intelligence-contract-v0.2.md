# IRL AI Core — Intelligence Contract v0.2

## 1. الحالة

- Contract: Intelligence Contract
- Version: v0.2
- Status: I-01 Final Draft — Pending Contract Review Gate
- Baseline: `main @ bfb597ba1cf4e9da05d522307a0ff1decb4d5d20`

---

## 2. الهدف

Intelligence هي طبقة تفسير وتحليل تقع بين Research وRecommendation.

هدفها تحويل مخرجات Research Evidence الموجودة في ResearchReport إلى إشارات منظمة وقابلة للتتبع تساعد طبقة Recommendation.

تشمل هذه الإشارات:

- تفسير النية
- اكتشاف الالتباس
- إشارات الموضوع
- إشارات أنواع المصادر
- الإشارات التجارية
- اعتبارات القرار
- الفجوات أو المعلومات غير الكافية

Intelligence لا تتخذ القرار النهائي.

---

## 3. الموضع المعماري

Research → Intelligence → Recommendation → Decision → Content Strategy → Content Brief → Draft → Editorial Cleanup → Media → Linking → Optimization → QA → Production Assembly → Article Package → Production Delivery Boundary → WordPress Delivery

Stage باسم `intelligence` موجود أصلًا ضمن الـ14 stages.

لا تتم إضافة Stage جديد.

---

## 4. المصدر Canonical

المصدر الأساسي لـ Intelligence هو `ResearchReport` ومخرجات Research Evidence والإشارات البحثية المرتبطة بها.

لا تنشئ Intelligence:

- ResearchReport جديدًا
- Search Intent model منافسًا
- Evidence خامًا مكررًا دون حاجة تعاقدية
- Recommendation
- Decision
- Content Strategy

---

## 5. Search Intent

`ResearchReport.search_intent` يبقى المصدر Canonical للـSearch Intent.

الحقل `intent_interpretation` هو تفسير للإشارات الموجودة في Research، ولا ينشئ نموذج Intent منافسًا أو يستبدل `ResearchReport.search_intent`.

---

## 6. هوية Intelligence

لكل Intelligence Artifact:

- `intelligence_id`
- `report_id`

`intelligence_id` هو Domain Artifact ID، ولا يدخل ضمن الـsix-ID production lineage.

الـsix-ID production lineage يبقى:

- `report_id`
- `decision_id`
- `strategy_id`
- `brief_id`
- `draft_id`
- `quality_id`

---

## 7. Evidence Traceability

كل إشارة جوهرية يجب أن تحتوي على `evidence_refs` وتشير إلى Evidence موجودة بالفعل.

لا يجوز إنشاء reference وهمي.

إذا كان المرجع مفقودًا أو غير موجود أو غير مرتبط بـ`report_id` الصحيح أو غير صالح، فيجب أن تفشل العملية Fail Closed.

---

## 8. Decision Signals

`decision_signals` تمثل اعتبارات مستخلصة من الأدلة. هي ليست Decision.

لا يجوز لـIntelligence أن تنتج قرارًا تشغيليًا مثل `approved` أو `rejected` أو `pursue` أو `defer` أو `reject`.

ولا يجوز لها إنشاء `decision_id` أو `recommendation_id` أو `strategy_id` كمتطلبات إنشاء.

---

## 9. Unsupported / Insufficient

يجب أن تحتوي Intelligence على `unsupported_or_insufficient` لتسجيل المعلومات غير الكافية، والاستنتاجات التي لا يمكن إثباتها، والفجوات البحثية، والقيود التي تمنع الثقة الكاملة.

الغرض هو منع الثقة الزائفة في مخرجات Intelligence.

---

## 10. Lifecycle

الحالة النهائية الصالحة لـIntelligence هي `intelligence_ready`.

ولا يجوز إعلان Intelligence جاهزة إذا لم تستوفِ schema validation وlineage validation وevidence reference validation وlifecycle validation.

---

## 11. الشكل الأساسي

```json
{
  "intelligence_id": "...",
  "report_id": "...",
  "intent_interpretation": {
    "summary": "...",
    "evidence_refs": []
  },
  "ambiguity": {
    "level": "...",
    "explanation": "...",
    "evidence_refs": []
  },
  "topic_signals": [],
  "source_type_signals": [],
  "commercial_signals": [],
  "decision_signals": [],
  "unsupported_or_insufficient": [],
  "schema_version": "...",
  "method_version": "...",
  "lifecycle_stage": "intelligence_ready"
}
```

---

## 12. Determinism

نفس المدخلات Canonical يجب أن تنتج نفس مخرجات Intelligence.

لا تعتمد Intelligence على نتائج عشوائية أو وقت التنفيذ أو ترتيب غير ثابت أو مصدر خارجي غير مثبت تعاقديًا.

---

## 13. External Providers

لا يتم إدخال مزود بحث أو API خارجي إلى Core مع حفظ بياناته داخل Research/Intelligence قبل حسم سياسة الاحتفاظ والـretention والحقوق المرتبطة بالبيانات.

---

## 14. Ownership Boundary

Research owns:

- البحث
- Evidence
- ResearchReport

Intelligence owns:

- interpretation
- signals
- ambiguity
- information gaps

Recommendation owns:

- recommendation
- priority
- scoring/rationale الخاصة به

Decision owns:

- operational decision

Content Strategy owns:

- production strategy

Intelligence لا تتجاوز هذه الحدود.

---

## 15. Orchestrator Integration Finding

### Finding ID

`I-01-ORCH-01`

### Component

`agents/research/production_orchestrator.py`

### Observation

الـOrchestrator يحتوي بالفعل على `intelligence` ضمن الـ14 stages.

لكن اكتشاف اكتمال الـstage حاليًا يعتمد على وجود `content_brief`، ويؤدي ذلك إلى اعتبار `intelligence` و`configuration` و`structure` مكتملة بصورة غير مباشرة.

### Contract Requirement

بعد إنشاء Intelligence Artifact مستقل، يجب ألا يكون وجود `content_brief` هو معيار اكتمال Intelligence.

يجب أن يرتبط اكتمال Stage `intelligence` بوجود Intelligence Artifact canonical صالح.

### Current Decision

`DEFERRED`

### Resolution Stage

`I-08 — Orchestrator Integration Review`

### I-01 Rule

لا يتم تعديل `production_orchestrator.py` ضمن I-01.

ولا يتم تغيير ترتيب الـ14 stages.

ولا يتم إضافة Stage جديد.

---

## 16. Invariants

1. لا Stage رقم 15.
2. لا تغيير في الـsix-ID production lineage.
3. لا استبدال `ResearchReport.search_intent`.
4. لا Recommendation داخل Intelligence.
5. لا Decision داخل Intelligence.
6. لا Content Strategy داخل Intelligence.
7. كل الإشارات الجوهرية قابلة للتتبع إلى Evidence.
8. المراجع غير الصالحة تؤدي إلى Fail Closed.
9. نفس المدخلات تنتج نفس المخرجات.
10. لا تعديل O7/G-01/G-02 دون ضرورة مثبتة.
11. لا Auto-Publish.
12. لا تعديل artifacts المحمية.

---

## 17. I-01 Review Result

Contract مقابل الكود الحالي:

- ResearchReport — PASS
- Evidence — PASS
- Search Intent — PASS
- Recommendation — PASS
- Decision — PASS
- Content Strategy — PASS
- Lifecycle — PASS
- Six-ID lineage — PASS
- Ownership boundaries — PASS
- Orchestrator — DEFERRED → I-08

Overall: `I-01 PASS — WITH DEFERRED ORCHESTRATOR FINDING`

---

## 18. Next Gate

الخطوة التالية: `I-02 — Contract Review Gate`.

ولا يبدأ `I-03 — JSON Schema` إلا بعد اعتماد هذا العقد.
