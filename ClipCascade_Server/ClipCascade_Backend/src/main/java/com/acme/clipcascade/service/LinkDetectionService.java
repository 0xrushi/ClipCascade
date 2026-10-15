package com.acme.clipcascade.service;

import java.net.URI;
import java.util.Optional;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import org.springframework.stereotype.Service;

import com.acme.clipcascade.constants.LinkType;

@Service
public class LinkDetectionService {

    private static final Pattern URL_PATTERN = Pattern.compile("https?://\\S+");

    public record DetectedLink(String url, LinkType type) {
    }

    /**
     * Extracts the first URL from a clipboard text payload and classifies it.
     * Returns empty when the payload contains no ingestible link (including
     * when the payload is E2E-encrypted ciphertext, which won't parse as a
     * URL).
     */
    public Optional<DetectedLink> detect(String payload) {
        if (payload == null || payload.isBlank()) {
            return Optional.empty();
        }

        Matcher matcher = URL_PATTERN.matcher(payload);
        if (!matcher.find()) {
            return Optional.empty();
        }

        String url = matcher.group().replaceAll("[)\\].,;'\"]+$", ""); // trim trailing punctuation
        String host = extractHost(url);
        if (host == null) {
            return Optional.empty();
        }

        LinkType type = classify(host);
        if (type == LinkType.NONE) {
            return Optional.empty();
        }
        return Optional.of(new DetectedLink(url, type));
    }

    private String extractHost(String url) {
        try {
            String host = URI.create(url).getHost();
            return host == null ? null : host.toLowerCase();
        } catch (IllegalArgumentException e) {
            return null;
        }
    }

    private LinkType classify(String host) {
        if (matches(host, "x.com") || matches(host, "twitter.com") || matches(host, "fxtwitter.com")) {
            return LinkType.TWITTER;
        }
        if (matches(host, "instagram.com") || matches(host, "kkinstagram.com")) {
            return LinkType.INSTAGRAM;
        }
        if (matches(host, "tiktok.com") || matches(host, "vm.tiktok.com")) {
            return LinkType.TIKTOK;
        }
        if (matches(host, "youtube.com") || matches(host, "youtu.be")) {
            return LinkType.YOUTUBE;
        }
        return LinkType.GENERIC_WEB;
    }

    private boolean matches(String host, String domain) {
        return host.equals(domain) || host.endsWith("." + domain);
    }
}
