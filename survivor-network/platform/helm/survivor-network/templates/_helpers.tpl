{{/*
Common labels
*/}}
{{- define "survivor-network.labels" -}}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/part-of: survivor-network
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version }}
{{- end }}

{{/*
Service selector labels
*/}}
{{- define "survivor-network.selectorLabels" -}}
app: {{ .name }}
{{- end }}

{{/*
Full image name
*/}}
{{- define "survivor-network.image" -}}
{{- if .global.imageRegistry -}}
{{ .global.imageRegistry }}/{{ .image.repository }}:{{ .image.tag }}
{{- else -}}
{{ .image.repository }}:{{ .image.tag }}
{{- end -}}
{{- end }}
