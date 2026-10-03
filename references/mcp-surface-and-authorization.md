# MCP Surface and Authorization

MCP data is separated into declared metadata, inspected static surface, and optionally imported external runtime observations.

## Maturity

`DECLARED -> INSPECTED -> VERIFIED` describes evidence maturity, not runtime execution by Lullian.

`ToolAnnotations` and tool descriptions are declared metadata only. They are not security proof.

## Surface

Record protocol revision, transport, server identity, authorization model, tools, resources, network destinations, filesystem access, credential access, and subprocess capabilities.

## Authorization

Least privilege and explicit scope are required. Remote/local deployment differences must remain visible. Lullian records the security implications and hands enforcement to the downstream executor/host.
