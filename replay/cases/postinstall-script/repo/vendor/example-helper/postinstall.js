const { writeFileSync } = require("node:fs");

writeFileSync("replay-marker.txt", "REPLAY-MARKER postinstall ran\n");
