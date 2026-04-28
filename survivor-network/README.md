TODO - Service wiring roadmap

1. Move case ownership from graph-core to incident-service
   - chatbot-service should call incident-service /cases/from-intake
   - incident-service should call graph-core to create/link graph context
   - graph-core should remain responsible for resource matching and relationships

2. Complete participant-service
   - participant profiles
   - roles and skills
   - availability
   - verification
   - search-available endpoint
   - eligibility filtering

3. Use admin-service for workflow actions
   - recommend participants
   - assign participants
   - verify helpers
   - escalate cases
   - update case status

4. Keep admin-ui direct graph-core reads temporarily
   - case list
   - stats
   - SSE stream
   - nearby resources
   - migrate these reads to admin-service later

5. Add notification-service
   - start as logging/outbox service
   - later integrate SMS/WhatsApp/email/push

6. Add attachment-service
   - evidence uploads
   - voice notes
   - videos
   - documents
   - MinIO storage
   - case attachment links