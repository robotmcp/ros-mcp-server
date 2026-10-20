// Apache-2.0. Only the Hub side is probed; no ROS or robot connection.
import assert from 'node:assert/strict';
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StreamableHTTPClientTransport } from '@modelcontextprotocol/sdk/client/streamableHttp.js';

const client = new Client({ name: 'robot-skill-hub-maintainer-probe', version: '1.0.0' });
const transport = new StreamableHTTPClientTransport(new URL('https://api.superfastrobotics.com/mcp'), {
  requestInit: {headers: {'DNT':'1', 'X-RSH-Telemetry':'off', 'X-RSH-Channel':'ros-mcp-example'}}
});
const unpack = result => {
  assert.equal(Boolean(result.isError), false, JSON.stringify(result.content));
  return result.structuredContent ?? JSON.parse(result.content.find(c => c.type === 'text').text);
};
try {
  await client.connect(transport);
  const tools = await client.listTools();
  assert(tools.tools.find(t => t.name === 'find_robot_skills'));
  const found = unpack(await client.callTool({name:'find_robot_skills',arguments:{q:'astar',runtime:'pythonrobotics',kind:'preparation_recipe',limit:1}}));
  assert.equal(found.results.length, 1);
  const selected = found.results[0];
  const inspected = unpack(await client.callTool({name:'inspect_robot_skill',arguments:{skill_id:selected.id,record_version:selected.record_version}}));
  assert.equal(inspected.record.id, selected.id);
  assert.equal(inspected.record.maintenance.record_version, selected.record_version);
  assert(inspected.record.interface);
  console.log(JSON.stringify({status:'passed',transport:'streamable-http',sdk:'1.32.1',tools:tools.tools.map(t=>t.name),selected:selected.id,hub_commit:inspected.hub_commit,record_version:selected.record_version,source_commit:inspected.record.source.commit,ros_connected:false,robot_executed:false,maintainer_probe:true}));
} finally {
  await client.close();
}
