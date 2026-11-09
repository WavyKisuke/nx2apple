// What Swift sees of the app's Objective-C: the data bookmark the Files app hands out (see
// DataBookmark.h). project.yml points SWIFT_OBJC_BRIDGING_HEADER here.
#import "DataBookmark.h"

/// YES only for a complete RomFS image or a folder accepted by the current game.
BOOL dm_game_data_url_is_valid(NSURL *url);
