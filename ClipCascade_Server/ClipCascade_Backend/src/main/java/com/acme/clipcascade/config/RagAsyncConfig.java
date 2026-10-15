package com.acme.clipcascade.config;

import java.util.concurrent.Executor;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.scheduling.concurrent.ThreadPoolTaskExecutor;

/**
 * Dedicated executor for @Async RAG dispatch, referenced by name so Spring
 * never has to disambiguate against the WebSocket message-broker executors
 * (clientInboundChannelExecutor, clientOutboundChannelExecutor, etc.).
 */
@Configuration
public class RagAsyncConfig {

    @Bean(name = "ragTaskExecutor")
    public Executor ragTaskExecutor() {
        ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();
        executor.setCorePoolSize(2);
        executor.setMaxPoolSize(4);
        executor.setQueueCapacity(100);
        executor.setThreadNamePrefix("rag-dispatch-");
        executor.initialize();
        return executor;
    }
}
