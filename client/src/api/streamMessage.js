import axios from 'axios';
import { API_BASE_URL } from '../utils/constants';
import { AUTH } from './endpoints';

/**
 * Server-Sent Events can't be read with axios (and EventSource can't send an
 * Authorization header), so streaming goes through fetch + a stream reader.
 */

async function refreshAccessToken() {
  const { data } = await axios.post(`${API_BASE_URL}${AUTH.REFRESH}`, {}, { withCredentials: true });
  localStorage.setItem('accessToken', data.access_token);
  return data.access_token;
}

function postStream(url, body, token, signal) {
  return fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    credentials: 'include',
    body: JSON.stringify(body),
    signal,
  });
}

/** Turn an error response body into a message safe to show the user. */
async function errorFromResponse(response) {
  let detail = null;
  try {
    const data = await response.json();
    if (typeof data?.detail === 'string') detail = data.detail;
  } catch {
    // non-JSON error body — fall through to the generic message
  }
  if (detail && (response.status < 500 || response.status === 503)) return detail;
  return "Couldn't get a response. Please try again.";
}

/**
 * Stream an assistant reply.
 *
 * `onEvent(name, payload)` is called for each server event:
 *   start  { mode, sources }   delta { text }
 *   model  { model_used }      done  { ...saved message }
 * Throws an Error with a user-friendly message if the request fails.
 */
export async function streamMessage({ chatId, body, onEvent, signal }) {
  const url = `${API_BASE_URL}/chats/${chatId}/messages/stream`;
  let token = localStorage.getItem('accessToken');

  let response = await postStream(url, body, token, signal);

  // Access token expired — refresh once, then retry
  if (response.status === 401) {
    try {
      token = await refreshAccessToken();
    } catch {
      localStorage.removeItem('accessToken');
      window.location.href = '/login';
      throw new Error('Your session expired. Please sign in again.');
    }
    response = await postStream(url, body, token, signal);
  }

  if (!response.ok) throw new Error(await errorFromResponse(response));
  if (!response.body) throw new Error('Streaming is not supported by this browser.');

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  // SSE frames are separated by a blank line; a frame may arrive in pieces
  const handleFrame = (frame) => {
    let name = 'message';
    const dataLines = [];
    for (const line of frame.split('\n')) {
      if (line.startsWith('event:')) name = line.slice(6).trim();
      else if (line.startsWith('data:')) dataLines.push(line.slice(5).trim());
    }
    if (!dataLines.length) return;
    try {
      onEvent(name, JSON.parse(dataLines.join('\n')));
    } catch {
      // ignore malformed frames rather than killing the stream
    }
  };

  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const frames = buffer.split('\n\n');
    buffer = frames.pop() ?? '';
    frames.forEach((frame) => frame.trim() && handleFrame(frame));
  }
  if (buffer.trim()) handleFrame(buffer);
}
