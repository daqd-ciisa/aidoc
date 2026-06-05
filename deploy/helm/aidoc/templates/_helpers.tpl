{{- define "aidoc.backendImage" -}}
{{ .Values.image.registry }}/{{ .Values.image.namespace }}/{{ .Values.image.backendRepo }}:{{ .Values.image.tag }}
{{- end -}}

{{- define "aidoc.frontendImage" -}}
{{ .Values.image.registry }}/{{ .Values.image.namespace }}/{{ .Values.image.frontendRepo }}:{{ .Values.image.tag }}
{{- end -}}

{{- define "aidoc.imagePullSecrets" -}}
{{- if .Values.imagePullSecrets }}
imagePullSecrets:
{{ toYaml .Values.imagePullSecrets | indent 2 }}
{{- end }}
{{- end -}}
