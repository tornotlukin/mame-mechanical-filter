// del_mech_xml.js
const fs = require('fs');
const { parseStringPromise, Builder } = require('xml2js');

async function extractCategories(inputPath, mechOutputPath, nonRunnableOutputPath, touchOutputPath) {
  try {
    // 1. Read and parse the original XML
    const xmlData = await fs.promises.readFile(inputPath, 'utf-8');
    const obj = await parseStringPromise(xmlData);

    // 2. Extract all <machine> entries
    const machines = obj.mame?.machine || [];

    // 3. Filter for mechanical and for non-runnable separately
    const mechanical  = machines.filter(m => m.$?.ismechanical === 'yes');
    const nonRunnable = machines.filter(m => m.$?.runnable === 'no');

    // 4. Filter for touch games by inspecting <control> elements in <input>
    const touchGames = machines.filter(m => {
      const controls = m.input?.[0]?.control || [];
      return controls.some(c => {
        const type = (c.$.type || '').toLowerCase();
        return type.includes('touch') || type.includes('position');
      });
    });

    // Helper: build and write an XML file
    const buildAndWrite = async (list, outPath) => {
      const outObj = { machines: { machine: list.map(m => ({ $: { name: m.$.name } })) } };
      const builder = new Builder({ headless: false, rootName: 'machines', renderOpts: { pretty: true } });
      const xml = builder.buildObject(outObj);
      await fs.promises.writeFile(outPath, xml, 'utf-8');
      console.log(`Wrote ${list.length} entries to ${outPath}`);
    };

    // 5. Write all three outputs
    await buildAndWrite(mechanical,    mechOutputPath);
    await buildAndWrite(nonRunnable,   nonRunnableOutputPath);
    await buildAndWrite(touchGames,    touchOutputPath);

  } catch (err) {
    console.error('Error:', err);
    process.exit(1);
  }
}

// CLI usage
const [ , , inFile, mechOut, nonRunOut, touchOut ] = process.argv;
if (!inFile || !mechOut || !nonRunOut || !touchOut) {
  console.error('Usage: node filter-machines.js <input.xml> <mechanical_out.xml> <nonRunnable_out.xml> <touch_out.xml>');
  process.exit(1);
}

extractCategories(inFile, mechOut, nonRunOut, touchOut);

