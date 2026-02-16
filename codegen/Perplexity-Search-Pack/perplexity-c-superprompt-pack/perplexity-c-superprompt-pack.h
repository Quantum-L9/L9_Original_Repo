/*
 * PERPLEXITY C INTEGRATION SUPERPROMPT PACK
 * ==========================================
 * 
 * Consolidated guide for C developers to use Perplexity API.
 * Covers: HTTP format, base64 attachments, web search, best practices.
 * 
 * USAGE: #include this header, use the macros and structs to build
 * JSON bodies and send via libcurl to https://api.perplexity.ai/chat/completions
 * 
 * Generated: 2026-01-15
 * Last updated: January 15, 2026
 */

#ifndef PERPLEXITY_C_SUPERPROMPT_PACK_H
#define PERPLEXITY_C_SUPERPROMPT_PACK_H

#include <stddef.h>
#include <stdint.h>

/* ============================================================================
   SECTION 1: API ENDPOINT & AUTHENTICATION
   ============================================================================ */

#define PERPLEXITY_API_BASE_URL    "https://api.perplexity.ai"
#define PERPLEXITY_CHAT_ENDPOINT   "https://api.perplexity.ai/chat/completions"
#define PERPLEXITY_SEARCH_ENDPOINT "https://api.perplexity.ai/search"

/* Recommended models (as of 2026-01-15) */
#define PERPLEXITY_MODEL_SONAR_PRO       "sonar-pro"
#define PERPLEXITY_MODEL_SONAR_REASONING "sonar-reasoning"
#define PERPLEXITY_MODEL_SONAR           "sonar"

/* Required header: Authorization: Bearer <API_KEY> */
#define PERPLEXITY_AUTH_HEADER_FORMAT "Authorization: Bearer %s"

/* ============================================================================
   SECTION 2: CORE SUPERPROMPTS (System + User Roles)
   ============================================================================ */

/* --- SUPERPROMPT 1: Simple Chat Query --- */
#define SUPERPROMPT_SIMPLE_SYSTEM \
  "You are a helpful AI assistant. Provide clear, accurate responses. " \
  "When citing information, always provide sources. Be concise but thorough."

#define SUPERPROMPT_SIMPLE_USER \
  "What is the current state of C library support for LLM APIs?"

/* --- SUPERPROMPT 2: File Analysis (Base64 Attachments) --- */
#define SUPERPROMPT_FILE_ANALYSIS_SYSTEM \
  "You are a document analysis expert. When given files: " \
  "1) Summarize key content. " \
  "2) Extract actionable insights. " \
  "3) Flag any critical issues or missing information. " \
  "4) Always cite specific sections or line numbers from the document. " \
  "Keep responses structured with clear headings and bullet points."

#define SUPERPROMPT_FILE_ANALYSIS_USER \
  "Analyze the attached C source file. Focus on: " \
  "1) Function signatures and error handling patterns. " \
  "2) Memory management (malloc/free, resource cleanup). " \
  "3) Security concerns (buffer overflows, input validation). " \
  "4) Opportunities for improvement. " \
  "Return a structured review with specific line numbers."

/* --- SUPERPROMPT 3: Deep Research (Web Search) --- */
#define SUPERPROMPT_RESEARCH_SYSTEM \
  "You are a research-grade analyst specializing in AI/ML integration. " \
  "Requirements: " \
  "(1) Always search the live web for current information. " \
  "(2) Read multiple independent sources before synthesizing. " \
  "(3) Use inline citations [source:N] and reference URLs. " \
  "(4) Flag uncertainty clearly ('limited sources', 'evolving field'). " \
  "(5) Prefer primary sources (official docs, peer-reviewed papers) over blogs. " \
  "(6) Never invent facts; skip if no credible sources found. " \
  "(7) Organize findings chronologically or by relevance."

#define SUPERPROMPT_RESEARCH_USER \
  "Deep research: Map the current landscape of C library integrations with LLM APIs. " \
  "Specifically: " \
  "1) Official libraries and SDKs (libcurl + wrappers, official C bindings). " \
  "2) Mature third-party libraries with >100 GitHub stars and active maintenance. " \
  "3) Performance benchmarks (throughput, latency, memory footprint). " \
  "4) Security best practices (API key handling, TLS verification, input sanitization). " \
  "5) Cost considerations (API pricing, rate limits, free tiers). " \
  "Return: Well-structured markdown report with inline [source:N] citations."

/* --- SUPERPROMPT 4: Base64 File Attachment Workflow --- */
#define SUPERPROMPT_BASE64_SYSTEM \
  "You are an expert in API integration and binary data encoding. " \
  "Context: Discussing base64 encoding of files for Perplexity API attachments. " \
  "Requirements: " \
  "1) Explain encoding/decoding steps clearly with code examples. " \
  "2) Address common gotchas (line breaks, padding, MIME type matching). " \
  "3) Provide concrete C code using standard library (no external base64 lib required). " \
  "4) Include error handling for truncated files or invalid base64. " \
  "5) Cite relevant specs (RFC 4648 for base64, official Perplexity docs for file_base64 format)."

#define SUPERPROMPT_BASE64_USER \
  "Explain how to: " \
  "1) Read a binary file (PDF, DOCX, PNG) into a C buffer. " \
  "2) Base64-encode that buffer without external libraries. " \
  "3) Embed the encoded string into a JSON 'file_base64' content block. " \
  "4) Handle edge cases: files >50MB, invalid encodings, timeout during POST. " \
  "Return: Runnable C code + explanation of each step + test cases."

/* --- SUPERPROMPT 5: Comprehensive C Integration Guide --- */
#define SUPERPROMPT_COMPREHENSIVE_SYSTEM \
  "You are an expert C systems programmer and API integration specialist. " \
  "This conversation has covered: " \
  "(A) Perplexity API format (OpenAI-compatible chat/completions). " \
  "(B) Authentication (Bearer token via Authorization header). " \
  "(C) Base64 file attachments (PDF/DOCX/TXT; max 50MB per file, 30 files per request). " \
  "(D) Web search super prompts (system role + user query + web_search_options params). " \
  "(E) Best practices (specific queries, semantic hints, source citation, error handling). " \
  "Style: Be practical, specific, and cite real code/API specs. Never invent details."

#define SUPERPROMPT_COMPREHENSIVE_USER \
  "Synthesize everything from this chat into a comprehensive C developer's guide. " \
  "Sections: " \
  "1. **HTTP Template** - libcurl setup, headers, endpoint, POST body structure. " \
  "2. **Base64 Workflow** - read file → encode → embed in JSON → POST. " \
  "3. **Web Search Super Prompts** - system role + user query + web_search_options. " \
  "4. **Error Handling** - invalid base64, file too large, timeout, network errors. " \
  "5. **Code Examples** - ready-to-compile snippets for: simple query, file summary, deep research. " \
  "6. **Limits & Performance** - file size, rate limits, latency tips. " \
  "7. **libcurl Quirks** - JSON escaping, memory management, cleanup patterns. " \
  "8. **Security** - API key storage, TLS verification, input sanitization. " \
  "Output: Structured markdown with inline code blocks and citations to Perplexity docs."

/* ============================================================================
   SECTION 3: FILE ATTACHMENT PARAMETERS
   ============================================================================ */

/* Maximum file sizes (Perplexity limits as of 2026-01) */
#define PERPLEXITY_MAX_FILE_SIZE_BYTES    (50 * 1024 * 1024)  /* 50 MB */
#define PERPLEXITY_MAX_FILES_PER_REQUEST  30

/* Supported MIME types for file_base64 blocks */
#define PERPLEXITY_MIME_TYPE_PDF          "application/pdf"
#define PERPLEXITY_MIME_TYPE_DOCX         "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
#define PERPLEXITY_MIME_TYPE_TXT          "text/plain"
#define PERPLEXITY_MIME_TYPE_RTF          "application/rtf"
#define PERPLEXITY_MIME_TYPE_MARKDOWN     "text/markdown"
#define PERPLEXITY_MIME_TYPE_JSON         "application/json"
#define PERPLEXITY_MIME_TYPE_CSV          "text/csv"
#define PERPLEXITY_MIME_TYPE_PNG          "image/png"
#define PERPLEXITY_MIME_TYPE_JPEG         "image/jpeg"
#define PERPLEXITY_MIME_TYPE_JPG          "image/jpg"

/* ============================================================================
   SECTION 4: WEB SEARCH OPTIONS (for Deep Research)
   ============================================================================ */

/* search_context_size values */
#define PERPLEXITY_SEARCH_CONTEXT_LOW     "low"
#define PERPLEXITY_SEARCH_CONTEXT_MEDIUM  "medium"
#define PERPLEXITY_SEARCH_CONTEXT_HIGH    "high"

/* search_recency values */
#define PERPLEXITY_SEARCH_RECENCY_DAY     "day"
#define PERPLEXITY_SEARCH_RECENCY_WEEK    "week"
#define PERPLEXITY_SEARCH_RECENCY_MONTH   "month"

/* Example search_domain_filter: for academic queries */
#define PERPLEXITY_DOMAIN_FILTER_ACADEMIC \
  "[\"arxiv.org\", \"scholar.google.com\", \"nature.com\", \"science.org\", \"researchgate.net\"]"

/* ============================================================================
   SECTION 5: BEST PRACTICES & PATTERNS
   ============================================================================ */

/*
 * PATTERN 1: Simple Query (No Attachments)
 * ========================================
 * Use this for quick factual questions without file context.
 * 
 * JSON Body:
 * {
 *   "model": "sonar-pro",
 *   "messages": [
 *     {
 *       "role": "system",
 *       "content": "You are a helpful C programming expert..."
 *     },
 *     {
 *       "role": "user",
 *       "content": "How do I use libcurl to POST JSON?"
 *     }
 *   ]
 * }
 */

/*
 * PATTERN 2: File Analysis with Base64 Attachment
 * ===============================================
 * For analyzing code, documents, or data files.
 * 
 * JSON Body (pseudo):
 * {
 *   "model": "sonar-pro",
 *   "messages": [
 *     {
 *       "role": "system",
 *       "content": "You are a code review expert..."
 *     },
 *     {
 *       "role": "user",
 *       "content": [
 *         { "type": "text", "text": "Review this C file for security issues." },
 *         {
 *           "type": "file_base64",
 *           "file_base64": {
 *             "data": "<BASE64_ENCODED_BYTES>",
 *             "mime_type": "text/plain",
 *             "file_name": "main.c"
 *           }
 *         }
 *       ]
 *     }
 *   ]
 * }
 * 
 * Key Points:
 * - Base64 encode the RAW file bytes only (no prefix like "data:...")
 * - Remove any line breaks from the base64 string before embedding in JSON
 * - Name the file clearly ("spec.pdf", "code_v2.c") and reference it in text
 * - Max 30 files per request, 50 MB each
 */

/*
 * PATTERN 3: Deep Research with Web Search
 * ========================================
 * For current events, trend analysis, or comprehensive research.
 * 
 * JSON Body (pseudo):
 * {
 *   "model": "sonar-pro",
 *   "messages": [
 *     {
 *       "role": "system",
 *       "content": "You are a research analyst. Always cite sources..."
 *     },
 *     {
 *       "role": "user",
 *       "content": "What are the latest C LLM integration libraries in 2026?"
 *     }
 *   ],
 *   "web_search_options": {
 *     "search_context_size": "high",
 *     "search_recency": "month"
 *   }
 * }
 * 
 * Key Points:
 * - Use "high" context size for deep research, "low" for quick facts
 * - Add search_recency to control freshness (day/week/month)
 * - Optionally add search_domain_filter for domain-specific queries
 * - Expect longer latency (5-15 sec) for high-context research
 */

/*
 * PATTERN 4: Multi-File Context
 * =============================
 * When you need context from multiple files.
 * 
 * JSON Body (pseudo):
 * {
 *   "model": "sonar-pro",
 *   "messages": [
 *     {
 *       "role": "user",
 *       "content": [
 *         { "type": "text", "text": "Compare these two API client implementations..." },
 *         {
 *           "type": "file_base64",
 *           "file_base64": {
 *             "data": "<BASE64_client_v1.c>",
 *             "mime_type": "text/plain",
 *             "file_name": "client_v1.c"
 *           }
 *         },
 *         {
 *           "type": "file_base64",
 *           "file_base64": {
 *             "data": "<BASE64_client_v2.c>",
 *             "mime_type": "text/plain",
 *             "file_name": "client_v2.c"
 *           }
 *         }
 *       ]
 *     }
 *   ]
 * }
 * 
 * Key Points:
 * - Add multiple file_base64 blocks in the same content array
 * - Keep minimum set of files needed (don't attach all 30 if 2 suffice)
 * - Reference files by name in your text prompt
 */

/* ============================================================================
   SECTION 6: ERROR HANDLING CHECKLIST
   ============================================================================ */

/*
 * Common Errors and Recovery:
 * 
 * 1. Invalid Base64
 *    - Symptom: "Invalid base64" in API response
 *    - Cause: Newlines in base64 string, wrong padding, truncated data
 *    - Fix: Remove all \n, verify length % 4 == 0, re-encode from source
 * 
 * 2. File Too Large
 *    - Symptom: "File exceeds maximum size"
 *    - Cause: File > 50 MB
 *    - Fix: Split file into chapters/sections, compress, or use URL if public
 * 
 * 3. Processing Timeout
 *    - Symptom: Request hangs for >30 sec, then fails
 *    - Cause: Large file + low search_context_size or complex analysis
 *    - Fix: Reduce file size, narrow question, or use lower search_context
 * 
 * 4. Network Error / Connection Refused
 *    - Symptom: libcurl CURLE_COULDNT_CONNECT
 *    - Cause: Wrong URL, firewall blocking, API down, or network issue
 *    - Fix: Verify endpoint URL, check firewall, retry with exponential backoff
 * 
 * 5. Unauthorized (401)
 *    - Symptom: "401 Unauthorized"
 *    - Cause: Invalid or expired API key, missing Bearer token
 *    - Fix: Verify PERPLEXITY_API_KEY env var, regenerate token in dashboard
 * 
 * 6. Rate Limit (429)
 *    - Symptom: "429 Too Many Requests"
 *    - Cause: Exceeded rate limit for your plan
 *    - Fix: Implement exponential backoff, throttle requests, upgrade plan
 * 
 * 7. Malformed JSON
 *    - Symptom: "Invalid JSON" or "Bad Request"
 *    - Cause: Unescaped quotes, missing commas, unmatched braces
 *    - Fix: Use printf debugger to print JSON before sending, validate syntax
 */

/* ============================================================================
   SECTION 7: SECURITY BEST PRACTICES
   ============================================================================ */

/*
 * API Key Management
 * ------------------
 * DO:
 *   - Store API key in PERPLEXITY_API_KEY environment variable
 *   - Never hardcode API key in source code
 *   - Rotate API keys regularly (monthly or on suspicion of compromise)
 *   - Use separate API keys for dev/staging/production
 * 
 * DON'T:
 *   - Log API keys or print them to stdout
 *   - Commit API keys to version control (add .env to .gitignore)
 *   - Share API keys with team members directly; use secrets manager
 *   - Use API keys over unencrypted HTTP (always use HTTPS)
 * 
 * TLS Verification (libcurl)
 * --------------------------
 * Always verify peer certificates in production:
 *   curl_easy_setopt(curl, CURLOPT_SSL_VERIFYPEER, 1L);
 *   curl_easy_setopt(curl, CURLOPT_SSL_VERIFYHOST, 2L);
 * 
 * Input Sanitization
 * ------------------
 * Before embedding user input in JSON:
 *   - Escape double quotes: " -> \"
 *   - Escape backslashes: \ -> \\
 *   - Escape newlines: \n (convert raw LF to escaped form)
 *   - Or use a JSON library (jansson, json-c) to build JSON safely
 * 
 * File Handling
 * -------------
 * When reading files for base64 encoding:
 *   - Verify file exists and is readable before opening
 *   - Check file size <= 50 MB before encoding
 *   - Use binary mode (fopen with "rb") for cross-platform compatibility
 *   - Properly close file handle and free memory after use
 * 
 * Memory Management
 * -----------------
 * - Use curl_slist_append() for headers, then curl_slist_free_all()
 * - If buffering response, free() the buffer when done
 * - Check malloc() return values before dereferencing pointers
 * - Consider valgrind or asan to detect leaks in development
 */

/* ============================================================================
   SECTION 8: LIBCURL HELPER SIGNATURES (Reference Only)
   ============================================================================ */

/*
 * Typical callback for writing response data:
 * 
 * static size_t write_callback(void *contents, size_t size, size_t nmemb, void *userp) {
 *     size_t realsize = size * nmemb;
 *     // Append to buffer or file
 *     return realsize;  // Return bytes processed; return 0 to abort
 * }
 * 
 * Setup call:
 * curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, write_callback);
 * curl_easy_setopt(curl, CURLOPT_WRITEDATA, (void *)buffer_or_file_ptr);
 */

/*
 * Typical base64 encoding signature (you can implement or use external lib):
 * 
 * char* base64_encode(const unsigned char *data, size_t input_length, size_t *output_length);
 * unsigned char* base64_decode(const char *data, size_t input_length, size_t *output_length);
 * 
 * Standard C doesn't include base64; use:
 *   - libb64 (lightweight, public domain)
 *   - openssl (base64 EVP functions; larger dependency)
 *   - home-rolled using RFC 4648 lookup table (compact)
 */

/* ============================================================================
   SECTION 9: REFERENCE LINKS & DOCUMENTATION
   ============================================================================ */

/*
 * Official Perplexity API Docs:
 *   - Quickstart: https://docs.perplexity.ai/getting-started/quickstart
 *   - Prompt Guide: https://docs.perplexity.ai/guides/prompt-guide
 *   - File Attachments: https://docs.perplexity.ai/guides/file-attachments
 *   - Image Attachments: https://docs.perplexity.ai/guides/image-attachments
 *   - Search Best Practices: https://docs.perplexity.ai/guides/search-best-practices
 *   - Models (Sonar, etc.): https://docs.perplexity.ai/getting-started/models/models/sonar
 * 
 * libcurl Documentation:
 *   - libcurl Easy Interface: https://curl.se/libcurl/c/libcurl-easy.html
 *   - HTTP POST: https://curl.se/libcurl/c/CURLOPT_POST.html
 *   - Custom Headers: https://curl.se/libcurl/c/CURLOPT_HTTPHEADER.html
 *   - Error Codes: https://curl.se/libcurl/c/libcurl-errors.html
 * 
 * Base64 Standards:
 *   - RFC 4648 (MIME Base64): https://tools.ietf.org/html/rfc4648
 * 
 * C JSON Libraries (optional):
 *   - jansson: https://jansson.readthedocs.io/
 *   - json-c: https://github.com/json-c/json-c/wiki
 */

/* ============================================================================
   SECTION 10: QUICK START TEMPLATE
   ============================================================================ */

/*
 * Minimal working example (pseudocode):
 * 
 * #include <curl/curl.h>
 * #include <stdio.h>
 * #include <stdlib.h>
 * #include <string.h>
 * 
 * static size_t write_cb(void *c, size_t sz, size_t nmemb, void *u) {
 *     fwrite(c, 1, sz*nmemb, stdout);
 *     return sz*nmemb;
 * }
 * 
 * int main(void) {
 *     const char *api_key = getenv("PERPLEXITY_API_KEY");
 *     if (!api_key) { fprintf(stderr, "No API key\n"); return 1; }
 * 
 *     CURL *curl = curl_easy_init();
 *     if (!curl) return 1;
 * 
 *     const char *json = "{"
 *         "\"model\":\"sonar-pro\","
 *         "\"messages\":["
 *             "{\"role\":\"user\",\"content\":\"What is C?\"}"
 *         "]"
 *     "}";
 * 
 *     char auth[256];
 *     snprintf(auth, sizeof(auth), "Authorization: Bearer %s", api_key);
 * 
 *     struct curl_slist *hdrs = NULL;
 *     hdrs = curl_slist_append(hdrs, auth);
 *     hdrs = curl_slist_append(hdrs, "Content-Type: application/json");
 * 
 *     curl_easy_setopt(curl, CURLOPT_URL, PERPLEXITY_CHAT_ENDPOINT);
 *     curl_easy_setopt(curl, CURLOPT_HTTPHEADER, hdrs);
 *     curl_easy_setopt(curl, CURLOPT_POSTFIELDS, json);
 *     curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, write_cb);
 * 
 *     CURLcode res = curl_easy_perform(curl);
 *     if (res != CURLE_OK)
 *         fprintf(stderr, "curl error: %s\n", curl_easy_strerror(res));
 * 
 *     curl_slist_free_all(hdrs);
 *     curl_easy_cleanup(curl);
 *     return (res == CURLE_OK) ? 0 : 1;
 * }
 * 
 * Compile & run:
 *   cc -o app main.c -lcurl
 *   export PERPLEXITY_API_KEY="your_key_here"
 *   ./app
 */

#endif /* PERPLEXITY_C_SUPERPROMPT_PACK_H */
