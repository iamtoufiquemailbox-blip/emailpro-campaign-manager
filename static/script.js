let currentRecipients = [];

// Upload CSV
document.getElementById('upload-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const fileInput = document.getElementById('csv-file');
  if (!fileInput.files[0]) return alert('Select a file first!');

  const formData = new FormData();
  formData.append('file', fileInput.files[0]);

  try {
    const res = await fetch('/api/upload', { method: 'POST', body: formData });
    const data = await res.json();
    if (res.ok) {
      currentRecipients = data.recipients || [];
      document.getElementById('metric-total').textContent = data.count;
      renderTable(currentRecipients);
      alert(data.message);
    } else {
      alert(data.error);
    }
  } catch (err) {
    alert('Failed to upload file.');
  }
});

// Run AI Classification
document.getElementById('classify-btn').addEventListener('click', async () => {
  const btn = document.getElementById('classify-btn');
  btn.textContent = '⏳ Classifying with Gemini...';
  btn.disabled = true;

  try {
    const res = await fetch('/api/classify', { method: 'POST' });
    const data = await res.json();
    if (res.ok) {
      currentRecipients = data.recipients || [];
      document.getElementById('metric-biz').textContent = data.business_count;
      document.getElementById('metric-ind').textContent = data.individual_count;
      renderTable(currentRecipients);
      alert('AI classification complete!');
    } else {
      alert(data.error);
    }
  } catch (err) {
    alert('Classification failed.');
  } finally {
    btn.textContent = '✨ Run AI Classification (Gemini)';
    btn.disabled = false;
  }
});

// Send Campaign
document.getElementById('campaign-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const btn = document.getElementById('send-btn');
  btn.textContent = '📨 Sending Emails...';
  btn.disabled = true;

  const formData = new FormData();
  formData.append('target', document.getElementById('target-segment').value);
  formData.append('subject', document.getElementById('campaign-subject').value);
  formData.append('body', document.getElementById('campaign-body').value);
  formData.append('recipients', JSON.stringify(currentRecipients));

  const file = document.getElementById('campaign-attachment').files[0];
  if (file) formData.append('attachment', file);

  try {
    const res = await fetch('/api/send-campaign', { method: 'POST', body: formData });
    const data = await res.json();
    if (res.ok) {
      currentRecipients = data.recipients || currentRecipients;
      document.getElementById('metric-delivered').textContent = data.delivered;
      renderTable(currentRecipients);
      alert(`Sent: ${data.delivered} | Failed: ${data.failed}`);
    } else {
      alert(data.error);
    }
  } catch (err) {
    alert('Campaign failed to send.');
  } finally {
    btn.textContent = '🚀 Send Bulk Campaign';
    btn.disabled = false;
  }
});

// Helper function to render table rows
function renderTable(recipients) {
  const tbody = document.getElementById('recipients-tbody');
  tbody.innerHTML = recipients
    .map((r) => `
      <tr class="border-b border-slate-700/50">
        <td class="py-2 text-slate-200">${r.email}</td>
        <td class="py-2">
          <span class="px-2 py-0.5 rounded text-xs ${
            r.category === 'Business'
              ? 'bg-blue-900 text-blue-300'
              : r.category === 'Individual'
              ? 'bg-purple-900 text-purple-300'
              : 'bg-slate-700 text-slate-300'
          }">${r.category}</span>
        </td>
        <td class="py-2">
          <span class="text-xs ${r.status === 'Delivered' ? 'text-emerald-400' : 'text-slate-400'}">${r.status}</span>
        </td>
      </tr>
    `)
    .join('');
}