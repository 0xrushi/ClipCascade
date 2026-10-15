package com.acme.clipcascade.service;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestClient;

import com.acme.clipcascade.config.ClipCascadeProperties;
import com.acme.clipcascade.constants.LinkType;
import com.acme.clipcascade.model.RagIngestRequest;

/**
 * Fire-and-forget dispatch of detected links to the RAG ingestion sidecar.
 * Failures are logged and swallowed so the clipboard sync path is never
 * affected.
 */
@Service
public class RagIngestionDispatcher {

    private static final Logger logger = LoggerFactory.getLogger(RagIngestionDispatcher.class);

    private final ClipCascadeProperties clipCascadeProperties;
    private final LinkDetectionService linkDetectionService;
    private final RestClient restClient;

    public RagIngestionDispatcher(
            ClipCascadeProperties clipCascadeProperties,
            LinkDetectionService linkDetectionService) {
        this.clipCascadeProperties = clipCascadeProperties;
        this.linkDetectionService = linkDetectionService;
        this.restClient = RestClient.builder()
                .baseUrl(clipCascadeProperties.getRagSidecarUrl())
                .build();
    }

    /**
     * Detects a link in the payload and, if found, posts it to the sidecar.
     * Runs on the async executor; safe to call inline from the message path.
     */
    @Async("ragTaskExecutor")
    public void detectAndDispatch(String payload, String type, String username) {
        if (!clipCascadeProperties.isRagEnabled()) {
            return;
        }

        // Only text payloads can contain a URL; encrypted payloads won't match
        if (type != null && !type.equals("text")) {
            return;
        }

        linkDetectionService.detect(payload).ifPresent(link -> dispatch(link, username));
    }

    private void dispatch(LinkDetectionService.DetectedLink link, String username) {
        RagIngestRequest request = new RagIngestRequest(
                link.url(),
                link.type() == LinkType.NONE ? LinkType.GENERIC_WEB : link.type(),
                username,
                System.currentTimeMillis());
        try {
            restClient.post()
                    .uri("/ingest")
                    .header("X-CCRAG-Token", clipCascadeProperties.getRagSidecarToken())
                    .body(request)
                    .retrieve()
                    .toBodilessEntity();
            logger.debug("RAG ingest dispatched: {}", link.url());
        } catch (Exception e) {
            logger.warn("RAG ingest dispatch failed for {} (user={}): {}",
                    link.url(), username, e.getMessage());
        }
    }
}
