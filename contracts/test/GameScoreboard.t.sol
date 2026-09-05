// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;
import "../src/GameScoreboard.sol";
interface Vm {
    function addr(uint256) external returns (address);
    function sign(uint256, bytes32) external returns (uint8, bytes32, bytes32);
    function prank(address) external;
    function expectRevert(bytes calldata) external;
    function warp(uint256) external;
}
contract GameScoreboardTest {
    Vm constant vm = Vm(address(uint160(uint256(keccak256("hevm cheat code")))));
    GameScoreboard board;
    uint256 constant KEY = 12345;
    address player = address(0xBEEF);
    bytes32 game = keccak256("game-one");
    function setUp() public { board = new GameScoreboard(vm.addr(KEY)); }
    function signature(bool correct, uint256 questions, uint256 deadline) internal returns(uint8, bytes32, bytes32) {
        bytes32 hash = keccak256(abi.encode(block.chainid, address(board), player, game, correct, questions, deadline));
        return vm.sign(KEY, keccak256(abi.encodePacked("\x19Ethereum Signed Message:\n32", hash)));
    }
    function testRecordsAndRejectsReplay() public {
        (uint8 v, bytes32 r, bytes32 s) = signature(true, 4, block.timestamp + 600);
        vm.prank(player);
        board.recordResult(game, true, 4, block.timestamp + 600, v, r, s);
        (uint256 games, uint256 correct, uint256 questions) = board.scores(player);
        require(games == 1 && correct == 1 && questions == 4);
        vm.expectRevert(bytes("Already recorded"));
        vm.prank(player);
        board.recordResult(game, true, 4, block.timestamp + 600, v, r, s);
    }
    function testRejectsOtherWalletAndTamperedResult() public {
        (uint8 v, bytes32 r, bytes32 s) = signature(true, 4, block.timestamp + 600);
        vm.expectRevert(bytes("Invalid signature"));
        board.recordResult(game, true, 4, block.timestamp + 600, v, r, s);
        vm.expectRevert(bytes("Invalid signature"));
        vm.prank(player);
        board.recordResult(game, false, 4, block.timestamp + 600, v, r, s);
    }
    function testRejectsExpired() public {
        (uint8 v, bytes32 r, bytes32 s) = signature(true, 4, 100);
        vm.warp(101);
        vm.expectRevert(bytes("Expired"));
        vm.prank(player);
        board.recordResult(game, true, 4, 100, v, r, s);
    }
    function testWrongGuessStillCountsGame() public {
        (uint8 v, bytes32 r, bytes32 s) = signature(false, 2, block.timestamp + 600);
        vm.prank(player);
        board.recordResult(game, false, 2, block.timestamp + 600, v, r, s);
        (uint256 games, uint256 correct, uint256 questions) = board.scores(player);
        require(games == 1 && correct == 0 && questions == 2);
    }
}
