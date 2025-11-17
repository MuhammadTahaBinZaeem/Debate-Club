export async function downloadTranscript(baseUrl, sessionId) {
  const response = await fetch(`${baseUrl}/export/${sessionId}`);
  if (!response.ok) {
    throw new Error('Unable to export PDF');
  }
  const blob = await response.blob();
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = `debate-${sessionId}.pdf`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}
