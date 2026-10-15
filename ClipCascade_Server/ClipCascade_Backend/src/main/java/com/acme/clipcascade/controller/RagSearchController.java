package com.acme.clipcascade.controller;

import java.security.Principal;

import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.client.RestClient;

import com.acme.clipcascade.config.ClipCascadeProperties;

/**
 * Proxies RAG search queries to the sidecar so that existing session
 * authentication guards access and users can only search their own clips.
 */
@RestController
public class RagSearchController {

    private final ClipCascadeProperties clipCascadeProperties;
    private final RestClient restClient;

    public RagSearchController(ClipCascadeProperties clipCascadeProperties) {
        this.clipCascadeProperties = clipCascadeProperties;
        this.restClient = RestClient.builder()
                .baseUrl(clipCascadeProperties.getRagSidecarUrl())
                .build();
    }

    @GetMapping("/rag/search")
    public ResponseEntity<String> search(
            Principal principal,
            @RequestParam("q") String query,
            @RequestParam(value = "limit", defaultValue = "8") int limit) {

        if (!clipCascadeProperties.isRagEnabled()) {
            return ResponseEntity.notFound().build();
        }

        String body = restClient.get()
                .uri(uriBuilder -> uriBuilder
                        .path("/search")
                        .queryParam("username", principal.getName())
                        .queryParam("q", query)
                        .queryParam("limit", limit)
                        .build())
                .header("X-CCRAG-Token", clipCascadeProperties.getRagSidecarToken())
                .retrieve()
                .body(String.class);

        return ResponseEntity.ok()
                .header("Content-Type", "application/json")
                .body(body);
    }
}
