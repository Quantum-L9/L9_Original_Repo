# Perplexity C Integration Superprompt Pack
## Implementation Guide & Quick Reference

**Version:** 1.0  
**Date:** January 15, 2026  
**Status:** Ready for Production  

---

## Table of Contents
1. [Quick Start](#quick-start)
2. [Five Essential Superprompts](#five-essential-superprompts)
3. [Base64 File Encoding Workflow](#base64-file-encoding-workflow)
4. [HTTP Request Template](#http-request-template)
5. [Error Handling Checklist](#error-handling-checklist)
6. [Security Best Practices](#security-best-practices)
7. [Complete Code Example](#complete-code-example)

---

## Quick Start

### 1. Include the Header
```c
#include "perplexity-c-superprompt-pack.h"
```

### 2. Set Environment Variable
```bash
export PERPLEXITY_API_KEY="your_api_key_from_perplexity_dashboard"
```

### 3. Link libcurl
```bash
cc -o my_app my_app.c -lcurl
```

### 4. Use a Superprompt
Choose from 5 ready-to-use superprompts:
- **Simple Chat** — factual questions
- **File Analysis** — code/document review
- **Deep Research** — web search + synthesis
- **Base64 Workflow** — file attachment guide
- **Comprehensive** — full integration guide

---

## Five Essential Superprompts

### Superprompt 1: Simple Chat Query
**Use for:** Quick factual questions, API clarifications, syntax help

**System Role:**
```
You are a helpful AI assistant. Provide clear, accurate responses. 
When citing information, always provide sources. Be concise but thorough.
```

**User Query:**
```
What is the current state of C library support for LLM APIs?
```

**Expected Output:** Concise list of libraries with brief descriptions.

---

### Superprompt 2: File Analysis
**Use for:** Code review, security auditing, document summarization

**System Role:**
```
You are a document analysis expert. When given files: 
1) Summarize key content. 
2) Extract actionable insights. 
3) Flag any critical issues or missing information. 
4) Always cite specific sections or line numbers from the document. 
Keep responses structured with clear headings and bullet points.
```

**User Query:**
```
Analyze the attached C source file. Focus on: 
1) Function signatures and error handling patterns. 
2) Memory management (malloc/free, resource cleanup). 
3) Security concerns (buffer overflows, input validation). 
4) Opportunities for improvement. 
Return a structured review with specific line numbers.
```

**How to attach a file:** Use `file_base64` content block (see section 3).

---

### Superprompt 3: Deep Research
**Use for:** Market research, trend analysis, comprehensive background

**System Role:**
```
You are a research-grade analyst specializing in AI/ML integration. 
Requirements: 
(1) Always search the live web for current information. 
(2) Read multiple independent sources before synthesizing. 
(3) Use inline citations [source:N] and reference URLs. 
(4) Flag uncertainty clearly ('limited sources', 'evolving field'). 
(5) Prefer primary sources (official docs, peer-reviewed papers) over blogs. 
(6) Never invent facts; skip if no credible sources found. 
(7) Organize findings chronologically or by relevance.
```

**User Query:**
```
Deep research: Map the current landscape of C library integrations with LLM APIs. 
Specifically: 
1) Official libraries and SDKs (libcurl + wrappers, official C bindings). 
2) Mature third-party libraries with >100 GitHub stars and active maintenance. 
3) Performance benchmarks (throughput, latency, memory footprint). 
4) Security best practices (API key handling, TLS verification, input sanitization). 
5) Cost considerations (API pricing, rate limits, free tiers). 
Return: Well-structured markdown report with inline [source:N] citations.
```

**API Parameters:**
```json
{
  "web_search_options": {
    "search_context_size": "high",
    "search_recency": "month"
  }
}
```

---

### Superprompt 4: Base64 Workflow
**Use for:** Understanding file encoding and attachment mechanics

**System Role:**
```
You are an expert in API integration and binary data encoding. 
Context: Discussing base64 encoding of files for Perplexity API attachments. 
Requirements: 
1) Explain encoding/decoding steps clearly with code examples. 
2) Address common gotchas (line breaks, padding, MIME type matching). 
3) Provide concrete C code using standard library (no external base64 lib required). 
4) Include error handling for truncated files or invalid base64. 
5) Cite relevant specs (RFC 4648 for base64, official Perplexity docs for file_base64 format).
```

**User Query:**
```
Explain how to: 
1) Read a binary file (PDF, DOCX, PNG) into a C buffer. 
2) Base64-encode that buffer without external libraries. 
3) Embed the encoded string into a JSON 'file_base64' content block. 
4) Handle edge cases: files >50MB, invalid encodings, timeout during POST. 
Return: Runnable C code + explanation of each step + test cases.
```

---

### Superprompt 5: Comprehensive Integration
**Use for:** Building a complete, production-ready C integration

**System Role:**
```
You are an expert C systems programmer and API integration specialist. 
This conversation has covered: 
(A) Perplexity API format (OpenAI-compatible chat/completions). 
(B) Authentication (Bearer token via Authorization header). 
(C) Base64 file attachments (PDF/DOCX/TXT; max 50MB per file, 30 files per request). 
(D) Web search super prompts (system role + user query + web_search_options params). 
(E) Best practices (specific queries, semantic hints, source citation, error handling). 
Style: Be practical, specific, and cite real code/API specs. Never invent details.
```

**User Query:**
```
Synthesize everything from this chat into a comprehensive C developer's guide. 
Sections: 
1. **HTTP Template** - libcurl setup, headers, endpoint, POST body structure. 
2. **Base64 Workflow** - read file → encode → embed in JSON → POST. 
3. **Web Search Super Prompts** - system role + user query + web_search_options. 
4. **Error Handling** - invalid base64, file too large, timeout, network errors. 
5. **Code Examples** - ready-to-compile snippets for: simple query, file summary, deep research. 
6. **Limits & Performance** - file size, rate limits, latency tips. 
7. **libcurl Quirks** - JSON escaping, memory management, cleanup patterns. 
8. **Security** - API key storage, TLS verification, input sanitization. 
Output: Structured markdown with inline code blocks and citations to Perplexity docs.
```

---

## Base64 File Encoding Workflow

### Step 1: Read File into Memory
```c
#include <stdio.h>
#include <stdlib.h>

// Read file into buffer
unsigned char* read_file(const char *filename, size_t *out_size) {
    FILE *fp = fopen(filename, "rb");
    if (!fp) return NULL;
    
    fseek(fp, 0, SEEK_END);
    long size = ftell(fp);
    fseek(fp, 0, SEEK_SET);
    
    if (size > 50 * 1024 * 1024) {  // 50 MB limit
        fprintf(stderr, "File too large: %ld bytes\n", size);
        fclose(fp);
        return NULL;
    }
    
    unsigned char *buf = (unsigned char*)malloc(size);
    if (!buf) {
        fclose(fp);
        return NULL;
    }
    
    size_t read = fread(buf, 1, size, fp);
    fclose(fp);
    
    if ((long)read != size) {
        free(buf);
        return NULL;
    }
    
    *out_size = read;
    return buf;
}
```

### Step 2: Encode to Base64
```c
// Simple base64 encoding (no external library required)
// Uses standard ASCII lookup table per RFC 4648

static const char base64_table[] = 
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";

char* base64_encode(const unsigned char *data, size_t len) {
    size_t out_len = ((len + 2) / 3) * 4 + 1;
    char *out = (char*)malloc(out_len);
    if (!out) return NULL;
    
    size_t idx = 0;
    for (size_t i = 0; i < len; i += 3) {
        unsigned char b1 = data[i];
        unsigned char b2 = (i + 1 < len) ? data[i + 1] : 0;
        unsigned char b3 = (i + 2 < len) ? data[i + 2] : 0;
        
        unsigned int n = (b1 << 16) | (b2 << 8) | b3;
        
        out[idx++] = base64_table[(n >> 18) & 0x3F];
        out[idx++] = base64_table[(n >> 12) & 0x3F];
        out[idx++] = (i + 1 < len) ? base64_table[(n >> 6) & 0x3F] : '=';
        out[idx++] = (i + 2 < len) ? base64_table[n & 0x3F] : '=';
    }
    out[idx] = '\0';
    return out;
}
```

### Step 3: Embed in JSON
```c
// Build JSON with embedded base64 file content
// Note: No line breaks in base64 string; escape quotes in filename

const char *json_template =
    "{"
    "  \"model\": \"sonar-pro\","
    "  \"messages\": ["
    "    {"
    "      \"role\": \"user\","
    "      \"content\": ["
    "        { \"type\": \"text\", \"text\": \"Summarize this PDF.\" },"
    "        {"
    "          \"type\": \"file_base64\","
    "          \"file_base64\": {"
    "            \"data\": \"%s\","
    "            \"mime_type\": \"application/pdf\","
    "            \"file_name\": \"report.pdf\""
    "          }"
    "        }"
    "      ]"
    "    }"
    "  ]"
    "}";

char json[MAX_JSON_SIZE];
snprintf(json, sizeof(json), json_template, base64_data);
```

### Step 4: POST to API
Use the HTTP template below.

---

## HTTP Request Template

### Using libcurl (Recommended)

```c
#include <curl/curl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

// Callback to handle response
static size_t write_callback(void *contents, size_t size, size_t nmemb, FILE *fp) {
    size_t realsize = size * nmemb;
    return fwrite(contents, 1, realsize, fp);
}

int post_to_perplexity(const char *api_key, const char *json_body) {
    CURL *curl = curl_easy_init();
    if (!curl) {
        fprintf(stderr, "curl_easy_init failed\n");
        return 1;
    }

    // Build Authorization header
    char auth_header[512];
    snprintf(auth_header, sizeof(auth_header), "Authorization: Bearer %s", api_key);

    // Setup headers
    struct curl_slist *headers = NULL;
    headers = curl_slist_append(headers, auth_header);
    headers = curl_slist_append(headers, "Content-Type: application/json");
    headers = curl_slist_append(headers, "Accept: application/json");

    // Configure request
    curl_easy_setopt(curl, CURLOPT_URL, "https://api.perplexity.ai/chat/completions");
    curl_easy_setopt(curl, CURLOPT_HTTPHEADER, headers);
    curl_easy_setopt(curl, CURLOPT_POST, 1L);
    curl_easy_setopt(curl, CURLOPT_POSTFIELDS, json_body);
    
    // TLS verification (IMPORTANT for security)
    curl_easy_setopt(curl, CURLOPT_SSL_VERIFYPEER, 1L);
    curl_easy_setopt(curl, CURLOPT_SSL_VERIFYHOST, 2L);
    
    // Response handling
    FILE *response_file = fopen("response.json", "wb");
    curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, write_callback);
    curl_easy_setopt(curl, CURLOPT_WRITEDATA, response_file);

    // Perform request
    CURLcode res = curl_easy_perform(curl);
    
    // Check for errors
    if (res != CURLE_OK) {
        fprintf(stderr, "curl_easy_perform failed: %s\n", curl_easy_strerror(res));
    } else {
        long http_code = 0;
        curl_easy_getinfo(curl, CURLINFO_RESPONSE_CODE, &http_code);
        printf("HTTP Response Code: %ld\n", http_code);
        if (http_code != 200) {
            fprintf(stderr, "API returned %ld\n", http_code);
        }
    }

    // Cleanup
    fclose(response_file);
    curl_slist_free_all(headers);
    curl_easy_cleanup(curl);

    return (res == CURLE_OK && http_code == 200) ? 0 : 1;
}
```

---

## Error Handling Checklist

| Error | Symptom | Cause | Fix |
|-------|---------|-------|-----|
| **Invalid Base64** | "Invalid base64" in response | Newlines in string, wrong padding, truncated | Remove `\n`, verify length % 4 == 0, re-encode |
| **File Too Large** | "File exceeds maximum size" | File > 50 MB | Split into chapters, compress, or host on web |
| **Processing Timeout** | Hangs >30 sec, then fails | Large file + complex analysis | Reduce file size, narrow question, lower context |
| **Network Error** | CURLE_COULDNT_CONNECT | Wrong URL, firewall, API down | Verify endpoint, check firewall, retry with backoff |
| **Unauthorized (401)** | "401 Unauthorized" | Invalid/expired API key, missing Bearer | Verify env var, regenerate token in dashboard |
| **Rate Limit (429)** | "429 Too Many Requests" | Exceeded rate limit | Implement exponential backoff, upgrade plan |
| **Malformed JSON** | "Invalid JSON" or "Bad Request" | Unescaped quotes, missing commas | Validate JSON before sending, use formatter |

---

## Security Best Practices

### 1. API Key Storage
```bash
# DO: Store in environment variable
export PERPLEXITY_API_KEY="sk_..." 

# DON'T: Hardcode in source
const char *api_key = "sk_...";  // NEVER!

# DON'T: Commit to Git
# Add .env to .gitignore
```

### 2. TLS Verification (Always On)
```c
// REQUIRED in production:
curl_easy_setopt(curl, CURLOPT_SSL_VERIFYPEER, 1L);
curl_easy_setopt(curl, CURLOPT_SSL_VERIFYHOST, 2L);

// Never disable these for "convenience"
```

### 3. Input Sanitization
```c
// Escape JSON strings before embedding
char* json_escape(const char *input) {
    // Convert: " -> \", \ -> \\, newline -> \n
    // Or use a JSON library (jansson, json-c)
}
```

### 4. File Handling
- Verify file exists and is readable
- Check file size <= 50 MB
- Use binary mode: `fopen(filename, "rb")`
- Properly free allocated buffers

### 5. Memory Management
```c
// Always check malloc/fopen return values
unsigned char *buf = (unsigned char*)malloc(size);
if (!buf) {
    perror("malloc failed");
    return 1;
}

// Free when done
free(buf);
```

---

## Complete Code Example

### `perplexity_client.c`
```c
#include <curl/curl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "perplexity-c-superprompt-pack.h"

#define MAX_JSON_SIZE 1000000  // 1 MB max JSON

// Response callback
static size_t write_cb(void *c, size_t sz, size_t nmemb, FILE *fp) {
    return fwrite(c, 1, sz * nmemb, fp);
}

// Simple query example
int simple_query(const char *api_key, const char *question) {
    CURL *curl = curl_easy_init();
    if (!curl) return 1;

    // Build JSON
    char json[MAX_JSON_SIZE];
    snprintf(json, sizeof(json),
        "{"
        "  \"model\": \"%s\","
        "  \"messages\": ["
        "    {\"role\": \"system\", \"content\": \"%s\"},"
        "    {\"role\": \"user\", \"content\": \"%s\"}"
        "  ]"
        "}", PERPLEXITY_MODEL_SONAR_PRO, SUPERPROMPT_SIMPLE_SYSTEM, question);

    // Setup request
    char auth[256];
    snprintf(auth, sizeof(auth), PERPLEXITY_AUTH_HEADER_FORMAT, api_key);

    struct curl_slist *hdrs = NULL;
    hdrs = curl_slist_append(hdrs, auth);
    hdrs = curl_slist_append(hdrs, "Content-Type: application/json");

    curl_easy_setopt(curl, CURLOPT_URL, PERPLEXITY_CHAT_ENDPOINT);
    curl_easy_setopt(curl, CURLOPT_HTTPHEADER, hdrs);
    curl_easy_setopt(curl, CURLOPT_POST, 1L);
    curl_easy_setopt(curl, CURLOPT_POSTFIELDS, json);
    curl_easy_setopt(curl, CURLOPT_SSL_VERIFYPEER, 1L);
    curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, write_cb);
    
    FILE *resp = fopen("response.json", "wb");
    curl_easy_setopt(curl, CURLOPT_WRITEDATA, resp);

    // Execute
    CURLcode res = curl_easy_perform(curl);
    
    if (res != CURLE_OK) {
        fprintf(stderr, "Error: %s\n", curl_easy_strerror(res));
    }

    fclose(resp);
    curl_slist_free_all(hdrs);
    curl_easy_cleanup(curl);
    
    return (res == CURLE_OK) ? 0 : 1;
}

int main(int argc, char *argv[]) {
    const char *api_key = getenv("PERPLEXITY_API_KEY");
    if (!api_key) {
        fprintf(stderr, "PERPLEXITY_API_KEY not set\n");
        return 1;
    }

    return simple_query(api_key, "Explain base64 encoding briefly.");
}
```

### Compile and Run
```bash
cc -o client perplexity_client.c -lcurl
export PERPLEXITY_API_KEY="your_key_here"
./client
cat response.json
```

---

## Summary

This superprompt pack provides:

✅ **5 Production-Ready Superprompts** — Simple chat, file analysis, deep research, base64 workflow, comprehensive guide

✅ **Base64 Encoding Workflow** — Step-by-step code for reading, encoding, embedding files

✅ **HTTP Template** — Drop-in libcurl integration with error handling

✅ **Security Guidelines** — API key management, TLS verification, input sanitization

✅ **Error Reference** — Common errors with diagnosis and fixes

✅ **Complete Examples** — Runnable C code

### Next Steps
1. Download `perplexity-c-superprompt-pack.h`
2. Include in your C project
3. Set `PERPLEXITY_API_KEY` environment variable
4. Link with `-lcurl`
5. Use one of the 5 superprompts to start

For questions or updates, visit: https://docs.perplexity.ai/

---

**End of Implementation Guide**
