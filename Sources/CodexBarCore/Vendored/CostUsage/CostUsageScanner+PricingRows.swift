import Foundation

extension CostUsageScanner {
    static func isCodexPremiumPricingMode(_ mode: String?) -> Bool {
        mode == "priority" || mode == "ultrafast"
    }

    static func codexResolvedCostUSD(
        for row: CodexUsageRow,
        priorityTurns: [String: CodexPriorityTurnMetadata] = [:],
        modelsDevCatalog: ModelsDevCatalog?,
        modelsDevCacheRoot: URL?,
        customPricing: CostUsageCustomPricing? = nil,
        pricingResolver: CostUsagePricing.CodexResolver? = nil) -> Double?
    {
        if let authoritativeCostNanos = row.knownCostNanos {
            return Double(authoritativeCostNanos) / self.costScale
        }
        let priorityMetadata = row.turnID.flatMap { priorityTurns[$0] }
        let isPriority = priorityMetadata != nil || CostUsageScanner.isCodexPremiumPricingMode(row.pricingMode)
        let pricedModel = priorityMetadata.map { self.codexPriorityPricingModel(for: row, priorityMetadata: $0) }
            ?? row.pricingModel
            ?? row.model
        let overlay = customPricing ?? .empty
        let pricingDate = row.timestampUnixMs.map { Date(timeIntervalSince1970: Double($0) / 1000) }
        // This personal fork displays the user's subscription consumption in API-price-equivalent USD.
        // Keep standard API token weights, apply subscription speed weights, and omit API context surcharges.
        let baseCost = CostUsagePricing.codexCostUSD(
            model: pricedModel,
            inputTokens: row.input,
            cachedInputTokens: row.cached,
            outputTokens: row.output,
            pricingDate: pricingDate,
            modelsDevCatalog: modelsDevCatalog,
            modelsDevCacheRoot: modelsDevCacheRoot,
            customPricing: overlay,
            pricingResolver: pricingResolver,
            applyLongContextRates: false)
        let multiplier: Double = row.pricingMode == "ultrafast" ? 8 : (isPriority ? 2.5 : 1)
        return baseCost.map { $0 * multiplier }
    }

    static func codexResolvedCostNanos(
        for row: CodexUsageRow,
        priorityTurns: [String: CodexPriorityTurnMetadata] = [:],
        modelsDevCatalog: ModelsDevCatalog?,
        modelsDevCacheRoot: URL?,
        customPricing: CostUsageCustomPricing? = nil) -> Int64?
    {
        guard let cost = self.codexResolvedCostUSD(
            for: row,
            priorityTurns: priorityTurns,
            modelsDevCatalog: modelsDevCatalog,
            modelsDevCacheRoot: modelsDevCacheRoot,
            customPricing: customPricing)
        else { return nil }
        let nanos = cost * self.costScale
        guard nanos.isFinite, nanos >= Double(Int64.min), nanos <= Double(Int64.max) else { return nil }
        return Int64(nanos.rounded())
    }

    static func codexRowsForReadTimePricing(_ usage: CostUsageFileUsage) -> [CodexUsageRow] {
        if let rows = usage.codexRows, !rows.isEmpty {
            return rows
        }
        return usage.days.flatMap { day, models in
            models.map { model, packed in
                CodexUsageRow(
                    day: day,
                    model: model,
                    turnID: nil,
                    eventIndex: nil,
                    input: packed[safe: 0] ?? 0,
                    cached: packed[safe: 1] ?? 0,
                    output: packed[safe: 2] ?? 0,
                    knownCostNanos: usage.codexCostNanos?[day]?[model],
                    pricingModel: model,
                    pricingMode: usage.codexPriorityTokens?[day]?[model] == nil ? "standard" : "priority")
            }
        }
    }

    static func codexPriorityPricingModel(
        for row: CodexUsageRow,
        priorityMetadata: CodexPriorityTurnMetadata) -> String
    {
        guard let model = priorityMetadata.model,
              CostUsagePricing.codexAPIFastMultiplier(model: model) != nil
        else { return row.model }
        return model
    }
}
