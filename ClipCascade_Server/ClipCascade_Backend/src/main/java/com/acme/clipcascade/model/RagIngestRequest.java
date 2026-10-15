package com.acme.clipcascade.model;

import com.acme.clipcascade.constants.LinkType;
import com.fasterxml.jackson.annotation.JsonProperty;

public class RagIngestRequest {

    private String url;

    @JsonProperty("link_type")
    private LinkType linkType;

    private String username;

    private long timestamp;

    public RagIngestRequest() {
    }

    public RagIngestRequest(String url, LinkType linkType, String username, long timestamp) {
        this.url = url;
        this.linkType = linkType;
        this.username = username;
        this.timestamp = timestamp;
    }

    public String getUrl() {
        return url;
    }

    public void setUrl(String url) {
        this.url = url;
    }

    public LinkType getLinkType() {
        return linkType;
    }

    public void setLinkType(LinkType linkType) {
        this.linkType = linkType;
    }

    public String getUsername() {
        return username;
    }

    public void setUsername(String username) {
        this.username = username;
    }

    public long getTimestamp() {
        return timestamp;
    }

    public void setTimestamp(long timestamp) {
        this.timestamp = timestamp;
    }

    @Override
    public String toString() {
        return "{" +
                " url='" + getUrl() + "'" +
                ", linkType='" + getLinkType() + "'" +
                ", username='" + getUsername() + "'" +
                ", timestamp='" + getTimestamp() + "'" +
                "}";
    }
}
